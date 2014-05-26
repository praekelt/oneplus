from distutils.core import setup, find_packages

setup(
    name='django-mobileu',
    version='1.04',
    packages=find_packages(),
    install_requires=[
        'Django==1.6.5',
        'South==0.8.4',
        'django-grappelli==2.5.3',
        'django-summernote==0.5.9',
        'Pillow==2.4.0',
    ],
    url='www.preakelt.co.za',
    license='',
    author='preakelt',
    author_email='info@preakelt.co.za',
    description='The MobileU MVP framework allows other developers to '
                'easily build mobile education sites.'
)
