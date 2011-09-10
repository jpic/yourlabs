Welcome to yourlabs's documentation!
====================================

This repo contains various Django *super simple* applications we use internally.

You want to read this page before using the following application specific
documentation shortcuts:

.. toctree::
   :maxdepth: 2

   runner

Applications
------------

yourlabs.runner
    It is frequent for projects to need commands to be executed continuously.
    When cron or spoolers aren't the way to go, runner provides a simple way to
    create background threads which chains commands continuously. For what it's
    worth, it's partly documented and we use it in production.

yourlabs.smoke
    High level tests, like testing if a view returns status 200, are called
    "smoke tests". This application makes creating complete smoke tests for all
    possible urls in your project easy. It's not really ready for a end user.

Install
-------

There is one repo for all apps, which is install easy to install::

    pip install -e git+git@github.com:yourlabs/yourlabs.git#egg=yourlabs

This will clone the repo in your-python-env/src/yourlabs and install the
yourlabs module. You can then install any application you like. For example,
install the "runner" applications by adding to settings.INSTALLED_APPS:
'yourlabs.runner'.

Note: you can hack directly in that repo.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
