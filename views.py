from django.views import generic
from .models import Product, ProductDetails
from django.conf import settings
from django.db.models import F, Q, Prefetch
from django.db.models import Count


class ProductListing(generic.ListView):
    template_name = 'main_page/index.html'
    context_object_name = 'product_list'
    paginate_by = 12


    def get_queryset(self):
        # Initializing the queryset
        products = Product.objects.annotate(
            name_shortened=F('more_details__name_shortened'),
            cpu_shortened=F('more_details__cpu_shortened'),
            gpu_shortened=F('more_details__gpu_shortened'),
            motherboard_shortened=F('more_details__motherboard_shortened'),
            ram_shortened=F('more_details__ram_shortened'),
            ssd_shortened=F('more_details__ssd_shortened'),
            gpu_model=F('more_details__gpu_model'),
            cpu_model=F('more_details__cpu_model'),

        ).all()

        # Capture filter options from query parameters
        filters = {
            'gpu': self.request.GET.getlist('gpu', ''),
            'cpu': self.request.GET.getlist('cpu', ''),
            'cpu_brand': self.request.GET.getlist('cpu_brand', ''),
            'gpu_series': self.request.GET.getlist('gpu_series', ''),
            'site': self.request.GET.getlist('site', ''),
            'search': self.request.GET.getlist('search', ''),
            'price_min': self.request.GET.get('minPrice', ''),
            'price_max': self.request.GET.get('maxPrice', '')
        }
        filter_status = False
        for filter_type, filter_values in filters.items():
            if filter_values:
                filter_status = True
                query = Q()
                for value in filter_values:
                    if filter_type == 'gpu':
                        query |= Q(more_details__gpu_model__iexact=value)
                    elif filter_type == 'cpu':
                        query |= Q(more_details__cpu_model__iexact=value)
                        value = value.replace(' ', '-')  # In case there is a - between i3-13200f
                        query |= Q(more_details__cpu_model__iexact=value)
                    elif filter_type == 'cpu_brand':
                        query |= Q(details__icontains=value)
                    elif filter_type == 'gpu_series':
                        query |= Q(more_details__gpu_model__icontains=value)
                    elif filter_type == 'site':
                        query |= Q(site__icontains=value)
                    elif filter_type == 'search':
                        query |= Q(details__icontains=value)
                        query |= Q(name__icontains=value)
                        query |= Q(site__icontains=value)
                    elif filter_type == 'search_hidden':
                        query |= Q(details__icontains=value)
                        query |= Q(name__icontains=value)
                        query |= Q(site__icontains=value)
                if filter_type == 'price_min' and filter_values.isdigit() and int(filter_values) >= 1:
                    query |= Q(price__gte=int(filter_values))
                elif filter_type == 'price_max' and filter_values.isdigit() and int(filter_values) >= 1:
                    query |= Q(price__lte=int(filter_values))

                print(query)
                products = products.filter(query)


        # Sorting options
        sort_options = {
            'suggested': '-added_date',
            'price': 'price',
            '-price': '-price',
            'bestvalue': 'difference',
        }

        sort_by = self.request.GET.get('sort', '')
        if sort_by in sort_options:
            products = products.order_by(sort_options[sort_by])
        #Filtering bestvalue if there is no sort option selected
        elif filter_status == False:
            products = products.order_by(sort_options['bestvalue'])



        return products
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        """Persisting sort, filtration parameters throughout pages"""
        context['current_sort'] = self.request.GET.get('sort', '')
        # Create a mutable copy of the GET dictionary
        query_params = self.request.GET.copy()

        # Remove parameter
        if 'page' in query_params:
            del query_params['page']

        if len(context['current_sort']) > 1:
            query_params['sort'] = context['current_sort']


        context['query_params'] = query_params.urlencode()

        """Take parameters list to show filter option. Appends tuple to list; RTX+4090, RTX 4090"""
        if len(query_params.urlencode()) > 1:
            parameters = query_params.urlencode().split('&')
            parameters_list = []
            for parameter in parameters:
                key, value = parameter.split('=')
                # Skip the 'sort' parameter remove first search value
                if key == 'search' and '&' in value:
                    value = value.split('&')[1]
                    parameters_list.append((key, value.replace('+', ' ').replace('&','')))
                elif key != 'sort':
                    parameters_list.append((key, value.replace('+', ' ')))

            context['parameter_list'] = parameters_list

        """Getting gpu_models for filtration section on the left"""
        """ USE ANNOTATE HERE"""
        rtx_gpu_models = ProductDetails.objects.filter(gpu_model__icontains='rtx') \
            .order_by('-gpu_model').values_list('gpu_model', flat=True).distinct()
        rx_gpu_models = ProductDetails.objects.filter(gpu_model__icontains='rx') \
            .order_by('-gpu_model').values_list('gpu_model', flat=True).distinct()
        all_gpu_models = list(rtx_gpu_models) + list(rx_gpu_models)
        context['all_gpu_models'] = all_gpu_models

        """Getting cpu_models for filtration section on the left"""
        intel_cpu_models = ProductDetails.objects.filter(cpu_model__icontains='i') \
            .order_by('-cpu_model').values_list('cpu_model', flat=True).distinct()
        amd_cpu_models = ProductDetails.objects.filter(cpu_model__icontains='ryzen') \
            .order_by('-cpu_model').values_list('cpu_model', flat=True).distinct()

        all_cpu_models = list(intel_cpu_models) + list(amd_cpu_models)
        context['all_cpu_models'] = all_cpu_models

        """Getting sites for filtration section on the left"""
        site_list = Product.objects.values_list('site', flat=True).distinct()
        context['list_of_sites'] = site_list

        """To persist filtration and keep check box checked after form submitted"""
        context['selected_gpu_models'] = self.request.GET.getlist('gpu')
        context['selected_cpu_models'] = self.request.GET.getlist('cpu')
        context['selected_cpu_brand'] = self.request.GET.getlist('cpu_brand')
        context['selected_gpu_series'] = self.request.GET.getlist('gpu_series')
        context['selected_site'] = self.request.GET.getlist('site')

        """Adding media url for logo"""
        context['MEDIA_URL'] = settings.MEDIA_URL

        return context


