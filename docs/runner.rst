yourlabs.runner
===============

It is frequent for projects to need commands to be executed continuously. When
cron or spoolers aren't the way to go, runner provides a simple way to create
background threads which chains commands continuously.

Install
-------

This app just provides a command: add 'yourlabs.runner' in your project's
settings.INSTALLED_APPS.

Usage
-----

Example usage for command run_functions::

    ./manage.py run_functions tasks.send_mail

This would continuously run the send_mail command if, for example, your project
root contained such a tasks.py file::

    from django.core.management import call_command

    def send_mail():
        call_command('send_mail')

Task chains
-----------

It can continuously run any number of tasks in the specified order::

    ./manage.py run_functions tasks.send_mail tasks.retry_deferred

The advantage of splitting tasks is monitoring and error reporting.

Cooldown time
-------------

A "cooldown" time should be adjusted in each task, on each server, to balance
between getting the job done and being resource-reasonnable, is easy with
time.sleep::

    import time
    
    from django.core.management import call_command

    def send_mail():
        call_command('send_mail')
        # 5 minutes cooldown
        time.sleep(5*60)

Customize privileges
--------------------

Running the tasks under a particular user is easy in bash, for example::

    su $username -c "source /srv/$domain/env/bin/activate && /srv/$domain/main/manage.py run_functions tasks.send_mail tasks.retry_deferred &>> /dev/null & disown"

Customize process priority
--------------------------

This example shows how to give priority to the runner of "gsm_sync_live" over
"-end_mail"::

    su $username -c "source /srv/$domain/env/bin/activate && nice -10 /srv/$domain/main/manage.py run_functions tasks.gsm_sync_live &>> /dev/null & disown"
    su $username -c "source /srv/$domain/env/bin/activate && nice 15 /srv/$domain/main/manage.py run_functions tasks.send_mail tasks.retry_deferred &>> /dev/null & disown"

To know more about process priorities and scheduling configuration, read the
manual of the nice command used in this example.

Advocacy
--------

Why make runner when there is cron ?
  Some tasks can take a while. And if the cron was every 24H hours and one day
  the task takes 24H, then the task would occupate two processes during an
  hour. We didn't want our tasks to run into race conditions. Also, if the task
  ends up taking 12H then we want it run twice in 24H.

Why not background the task in a spooler like uWSGI, celery, ztask ... ?
  Using a spooler to have some tasks run continuously is like using a rock to
  sharpen a stick.
