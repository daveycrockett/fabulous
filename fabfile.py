from fabric.api import local, abort, run, lcd, cd, settings, sudo, env
from fabric.contrib.console import confirm

PROJECTS = ['igreport']

def deploy(project='all', dest='test', fix_owner='True', syncdb='False', south='False', south_initial='False', init_data='False', hash='False', base_git_user='mpeirwe'):
    if not dest in ['prod', 'test']:
        abort('must specify a valid dest: prod or test')
    if project != 'all' and project not in PROJECTS \
        and not confirm("Project %s not in known projects (%s), proceed anyway?" % (project, PROJECTS)):
        abort('must specify a valid project: all or one of %s' % PROJECTS)
    projects = PROJECTS if project == 'all' else [project]
    for p in projects:
        # /var/www/test/upreport, e.g.
        code_dir = "/var/www/%s/%s/" % (dest, p)
        with settings(warn_only=True):
            if run("test -d %s" % code_dir).failed:
                run("git clone git://github.com/%s/%s %s" % (base_git_user, p, code_dir))
                with cd(code_dir):
                    run("git config core.filemode false")
        with cd(code_dir):
            if hash == 'False':
                run("git pull origin master")
            else:
                run("git checkout %s" % hash)
            run("git submodule init")
            run("git submodule sync")
            run("git submodule update")
            run("git submodule foreach git config core.filemode false")
            with cd("%s_project" % p):
                if syncdb == 'True':
                    run("/opt/env/%s/bin/python manage.py syncdb" % dest)
                if south == 'True':
                    run("/opt/env/%s/bin/python manage.py migrate" % dest)
                else:
                    if confirm('Check for pending migrations?', default=False):
                        run("/opt/env/%s/bin/python manage.py migrate --list | awk '$0 !~ /\*/ && $0 !~ /^$/' " % dest)
                if init_data == 'True':
                   # in mtrack, this loads initial data
                   # which doesn't specifically mean fixtures (which are loaded during syncdb and  migrations)
                   run("/opt/env/%s/bin/python manage.py %s_init" % (dest, p))
                if south_initial == 'True':
                    run("/opt/env/%s/bin/python manage.py migrate --fake" % dest)
                    run("/opt/env/%s/bin/python manage.py migrate" % dest)

        if not fix_owner == 'False':
            with cd("%s../" % code_dir):
                sudo("chown -R www-data:www-data %s" % p)
                sudo("chmod -R ug+rwx %s" % p)

        if dest == 'prod':
            with cd(code_dir):
                with settings(warn_only=True):
                    sudo("cp cron_* /etc/cron.d/")

        proc_name = "test%s_uwsgi" % p if dest == 'test' else '%s_uwsgi' % p
        sudo("supervisorctl restart %s" % proc_name)

