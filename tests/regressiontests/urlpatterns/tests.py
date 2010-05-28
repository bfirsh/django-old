from django.test import TestCase

class TestResolver(TestCase):
    urls = 'regressiontests.urlpatterns.urls'
    
    def test_callable_view(self):
        response = self.client.get('/callable-view/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'callable_view')
    
    def test_string_view(self):
        response = self.client.get('/string-view/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'string_view')
    
    def test_new_instance_of_class_for_request(self):
        """
        When a class is passed as a view, ensure a new instance is created for
        each request.
        """
        response = self.client.get('/class/new-instance/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'OneTimeView')
        # This view will 404 if it is called a second time
        self.assertEqual(
            self.client.get('/class/new-instance/').status_code,
            200
        )
    
    def test_class_string_view(self):
        """
        Test class views can be passed as strings.
        """
        response = self.client.get('/class/string/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'StringView')
        # Ensure new instances are creating for string views too
        self.assertEqual(self.client.get('/class/string/').status_code, 200)

