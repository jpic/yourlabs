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

::

    <<< 22:50.31 Sun Sep 11 2011!~bet_prod/main 
    <<< root@tina!12456 E:130 S:1 G:master bet_prod_env
    >>> source ../local && start_runner
    Starting run_functions tasks.gsm_sync tasks.update_index                                                                                                               Starting run_functions tasks.gsm_sync_live
    Starting run_functions tasks.send_mail tasks.retry_deferred
    <<< 22:50.33 Sun Sep 11 2011!~bet_prod/main 
    <<< root@tina!12462 S:1 G:master bet_prod_env
    >>> ps aux | grep run_functions
    bet_prod 24499  2.3  1.2  33744 25644 pts/3    SN   22:46   0:05 python /srv/bet_prod/main/manage.py run_functions tasks.gsm_sync tasks.update_index                   bet_prod 24502  7.5  1.2  34128 26092 pts/3    SN   22:46   0:18 python /srv/bet_prod/main/manage.py run_functions tasks.gsm_sync_live
    bet_prod 24505  0.7  1.2  32568 24412 pts/3    SN   22:46   0:01 python /srv/bet_prod/main/manage.py run_functions tasks.send_mail tasks.retry_deferred
    bet_prod 24626 18.0  0.3  12328  7072 pts/3    RN   22:50   0:00 python /srv/bet_prod/main/manage.py run_functions tasks.gsm_sync tasks.update_index
    bet_prod 24629 57.0  0.6  17536 12380 pts/3    RN   22:50   0:00 python /srv/bet_prod/main/manage.py run_functions tasks.gsm_sync_live
    bet_prod 24632  2.0  0.1   6624  2920 pts/3    RN   22:50   0:00 python /srv/bet_prod/main/manage.py run_functions tasks.send_mail tasks.retry_deferred
    root     24639  0.0  0.0   4408   836 pts/3    S+   22:50   0:00 grep run_functions
    <<< 22:50.34 Sun Sep 11 2011!~bet_prod/main 
    <<< root@tina!12463 S:1 G:master bet_prod_env
    >>> ps aux | grep run_functions 
    bet_prod 24626 15.1  1.2  32868 24808 pts/3    RN   22:50   0:02 python /srv/bet_prod/main/manage.py run_functions tasks.gsm_sync tasks.update_index
    bet_prod 24629 17.6  1.2  33804 25876 pts/3    SN   22:50   0:02 python /srv/bet_prod/main/manage.py run_functions tasks.gsm_sync_live
    bet_prod 24632 13.8  1.2  32564 24412 pts/3    SN   22:50   0:01 python /srv/bet_prod/main/manage.py run_functions tasks.send_mail tasks.retry_deferred
    root     24663  0.0  0.0   4408   836 pts/3    S+   22:50   0:00 grep run_functions


Historical context
------------------

A project needs to continuously run tasks (duh!). Several chains of API calls
must to be done with different intervals, to ensure a balance between data
freshness and performance. Needless to say, this is a mission critical task.

The first attempt was using threads but it turned out everything had to be done
to have sane monitoring. First i implemented exception handling in one task.
Then, refactored it to use it in another task.

runner.Runner was born. However, it did not make sense to carry the weight of
thread management anymore. The command run_functions was born. It really looked
handy and it was a sunny day so it was open sourced.
