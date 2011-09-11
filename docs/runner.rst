yourlabs.runner
===============

It is frequent for projects to need commands to be executed continuously. When
cron or spoolers aren't the way to go, runner provides a simple way to create
background threads which chains commands continuously.

Install
-------

This app just provides a command: add `yourlabs.runner` in your project's
`settings.INSTALLED_APPS`.

Also, runner expects the following settings:

    - `settings.LOGGING['loggers']['runner']`: your logger config
    - `settings.RUN_ROOT`: the path where it should create it's pidfiles

Usage
-----

Example usage for command `run_functions`::

    ./manage.py run_functions tasks.send_mail

This would continuously run the `send_mail` command if, for example, your project
root contained such a `tasks.py` file::

    from django.core.management import call_command

    def send_mail():
        call_command('send_mail')

Task chains
```````````

It can continuously run any number of tasks in the specified order::

    ./manage.py run_functions tasks.send_mail tasks.retry_deferred

The advantage of splitting tasks is monitoring and error reporting.

Cooldown time
`````````````

A `cooldown` time should be adjusted in each task, on each server, to balance
between getting the job done and being resource-reasonnable, is easy with
`time.sleep`::

    import time
    
    from django.core.management import call_command

    def send_mail():
        call_command('send_mail')
        # 5 minutes cooldown
        time.sleep(5*60)

Customize privileges
````````````````````

Running the tasks under a particular user is easy in bash, for example::

    su $username -c "source /srv/$domain/env/bin/activate && \
        nice -n 5 /srv/$domain/main/manage.py run_functions \
            tasks.send_mail \
            tasks.retry_deferred \
        &>> /srv/$domain/log/runner_debug_0 & disown"

Customize process priority
``````````````````````````

This example shows how to give priority to the runner of `gsm_sync_live` over
the `send_mail_retry_deferred` runner::

    su $username -c "source /srv/$domain/env/bin/activate && \
        nice -n 5 /srv/$domain/main/manage.py run_functions \
            tasks.gsm_sync_live \
    &>> /dev/null & disown"
    su $username -c "source /srv/$domain/env/bin/activate && \
        nice -n 15 /srv/$domain/main/manage.py run_functions \
            tasks.send_mail \
            tasks.retry_deferred \
    &>> /dev/null & disown"

To know more about process priorities and scheduling configuration, read the
manual of the nice command used in this example.

Maintenance
-----------

One of the main goals of `yourlabs.runner` is to require as low maintenance as
possible.

Monitoring
``````````

A runner resets a task's consecutive executions counter when it succeedes.
Otherwise:

- it logs the failure with a `warning`
- if it's not the first time it will log an error, it will log an `error`
- or if there were a multiple of 5 consecutive failures (5, 10, 15, etc, etc
  ..) it will log a `critical`

Note that it will mail admins, with all the consecutive exceptions and
traceback, whenever it logs a critical message.

For each consecutive failure, such a report is appended to the administrator email message::

    Message: 'function' object has no attribute '_Runner__name'
    Date/Time: 2011-09-10 20:59:44.518869
    Exception class: AttributeError
    Traceback:
    Traceback (most recent call last):
     File "/srv/bet_prod/bet_prod_env/src/yourlabs/yourlabs/runner/__init__.py", line 94, in run
       function.__name)
    AttributeError: 'function' object has no attribute '_Runner__name'

Concurrency handling
````````````````````

Each runner will create a pidfile in `RUN_ROOT`, for example
`PROJECT_ROOT/var/run/send_mail_retry_deferred.pid` for `run_functions
tasks.send_mail tasks.retry_deferred` if `RUN_ROOT` is set to `PROJECT_ROOT +
'/var/run/`

The runner doesn't even attempt to delete its pidfile on exit. It keeps in mind
that a dead pidfile might be left for example after a power outage.

When a runner starts, it checks if a pidfile exists and unless option
`killconcurrent` is set to False, it will attempt to kill the existing process if
any. Anyway, it will delete and re-create the pidfile with the actual pid.

This is implemented in the `runner.Runner.concurrency_security` method.

However, if a concurrent runner checks for the pidfile **before** the other one
writes it, then it will result in concurrent processes. That should only happen
during stress tests.

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
