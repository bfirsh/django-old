from django.http import HttpResponse, Http404

def callable_view(request):
    return HttpResponse('callable_view')

def string_view(request):
    return HttpResponse('string_view')

class OneTimeView(object):
    """
    A view that will 404 the second time it is called.
    """
    
    has_been_called = False
    
    def __call__(self, request):
        if self.has_been_called:
            raise Http404
        self.has_been_called = True
        return HttpResponse(self.__class__.__name__)


class StringView(OneTimeView):
    pass

