# -*- coding: utf-8 -*-
import os

from fabric.api import *
from fabric.contrib.files import upload_template

CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))

# ----------------------------------------------------------------
# ALTERAR CONFIGURAÇÕES BASEADAS NO SEUS SERVIDOR E MAQUINA LOCAL
# ----------------------------------------------------------------

# SERVIDOR
user = 'root'
host = '192.168.0.1'
chave = '' # caminho da chave nome_arquivo.pem

# LOCAL
bitbucket_user = 'conta'
bitbucket_project_default = 'projeto_padrao'
folder_project_local = '~/projetos/'

# copiar as variaveis de cima e jogar no local_settings para substituir
try:
    from local_settings import *
except ImportError:
    pass

# --------------------------------------------------------

prod_server = '{0}@{1}'.format(user, host)
project_path = '/home/'

# diretório do conf.d do supervisor
env.supervisor_conf_d_path = '/etc/supervisor/conf.d'

# nome da conta
env.conta = ''

# dominio da conta
env.dominio = ''

# linguagem 1-python 2-php
env.linguagem = ''

# senha do root do mysql
env.mysql_password = ''

# porta para rodar o projeto
env.porta = ''

# diretório do sites-enable do nginx
env.nginx_sites_enable_path = '/etc/nginx/sites-enabled'

env.hosts = [prod_server]

# endereco da chave
env.key_filename = chave


# --------------------------------------------------------
# SERVIDOR
# --------------------------------------------------------

def newserver():
    # gera uma chave no servidor para utilizar o comando upload_public_key
    run('ssh-keygen')

    """Configurar e instalar todos pacotes necessários para servidor"""
    log('Configurar e instalar todos pacotes necessários para servidor')

    update_server()

    update_server()
    upgrade_server()

    # pacotes
    build_server()
    python_server()
    mysql_server()
    git_server()
    outros_server()

    # atualizando
    update_server()
    upgrade_server()

    # nginx
    try:
        sudo('mv /etc/nginx/nginx.conf /etc/nginx/nginx_backup.conf')
    except:
        pass
    write_file('nginx_server.conf', '/etc/nginx/nginx.conf')
    nginx_restart()

    # supervisor
    try:
        sudo('mv /etc/supervisor/supervisord.conf /etc/supervisor/supervisord_backup.conf')
    except:
        pass
    write_file('supervisord_server.conf', '/etc/supervisor/supervisord.conf')
    supervisor_restart()

    # funcionar thumbnail no ubuntu 64bits
    sudo("ln -s /usr/lib/'uname -i'-linux-gnu/libfreetype.so /usr/lib/")
    sudo("ln -s /usr/lib/'uname -i'-linux-gnu/libjpeg.so /usr/lib/")
    sudo("ln -s /usr/lib/'uname -i'-linux-gnu/libz.so /usr/lib/")

    log('Reiniciando a máquina')
    reboot()

# cria uma conta no servidor
def novaconta():
    """Criar uma nova conta do usuário no servidor"""
    log('Criar uma nova conta do usuário no servidor')

    # criando usuario
    if not env.conta:
        env.conta = raw_input('Digite o nome da conta: ')
    if not env.dominio:
        env.dominio = raw_input('Digite o domínio do site: ')
    if not env.linguagem:
        env.linguagem = raw_input('Linguagens disponíveis\n\n1) PYTHON\n2) PHP\n\nEscolha a linguagem: ')
        if not env.porta and env.linguagem == 1:
            env.porta = raw_input('Digite o número da porta: ')
    if not env.mysql_password:
        env.mysql_password = raw_input('Digite a senha do ROOT do MySQL: ')

    # cria usuario no linux
    user_senha = gera_senha(12)
    adduser(env.conta, user_senha)

    run('mkdir /home/{0}/logs'.format(env.conta))
    run('touch /home/{0}/logs/access.log'.format(env.conta))
    run('touch /home/{0}/logs/error.log'.format(env.conta))

    if env.linguagem == 1:
        run('virtualenv /home/{0}/env --no-site-packages'.format(env.conta))
        write_file('nginx.conf', '/home/{0}/nginx.conf'.format(env.conta))
        write_file('supervisor.ini', '/home/{0}/supervisor.ini'.format(env.conta))
        write_file('bash_login', '/home/{0}/.bash_login'.format(env.conta))
    else:
        write_file('nginx_php.conf', '/home/{0}/nginx.conf'.format(env.conta))
        run('mkdir /home/{0}/public_html/'.format(env.conta))

    # cria banco e usuario no banco
    banco_senha = gera_senha(12)
    newbase(env.conta, banco_senha)

    # da permissao para o usuario no diretorio
    sudo('chown -R {0}:{0} /home/{0}'.format(env.conta))

    nginx_restart()
    supervisor_restart()

    # log para salvar no docs
    log('Anotar dados da conta')
    print '{0} \nUSUÁRIO senha: {1} \nBANCO senha: {2}'.format(env.conta, user_senha, banco_senha)

def write_file(filename, destination):

    upload_template(
            filename=filename,
            destination=destination,
            template_dir=os.path.join(CURRENT_PATH, 'inc'),
            context=env,
            use_jinja=True,
            use_sudo=True,
            backup=False
        )

# deleta uma conta no servidor
def delconta():
    """Deletar conta no servidor"""
    conta = raw_input('Digite o nome da conta: ')
    env.mysql_password = raw_input('Digite a senha do ROOT do MySQL: ')
    log('Deletando conta {0}'.format(conta))
    userdel(conta)
    dropbase(conta)


# cria usuario no servidor
def adduser(conta=None, user_senha=None):
    """Criar um usuário no servidor"""

    if not user_senha:
        user_senha = gera_senha(12)
    print 'senha usuário: {0}'.format(user_senha)

    if not conta:
        conta = raw_input('Digite o nome do usuário: ')

    log('Criando usuário {0}'.format(conta))
    sudo('adduser {0}'.format(conta))


# MYSQL - cria usuario e banco de dados
def newbase(conta=None, banco_senha=None):
    """Criar banco de dados e usuário no servidor"""

    if not banco_senha:
        banco_senha = gera_senha(12)
    print 'Senha gerada para o banco: {0}'.format(banco_senha)

    if not conta:
        conta = raw_input('Digite o nome do banco: ')
    log('NEW DATABASE {0}'.format(conta))

    # cria acesso para o banco local
    sudo("echo CREATE DATABASE {0} | mysql -u root -p{1}".format(conta, env.mysql_password))
    sudo("echo \"CREATE USER '{0}'@'localhost' IDENTIFIED BY '{1}'\" | mysql -u root -p{2}".format(conta, banco_senha, env.mysql_password))
    sudo("echo \"GRANT ALL PRIVILEGES ON {0} . * TO '{0}'@'localhost'\" | mysql -u root -p{1}".format(conta, env.mysql_password))

    # cria acesso para o banco remoto
    sudo("echo \"CREATE USER '{0}'@'%' IDENTIFIED BY '{1}'\" | mysql -u root -p{2}".format(conta, banco_senha, env.mysql_password))
    sudo("echo \"GRANT ALL PRIVILEGES ON {0} . * TO '{0}'@'%'\" | mysql -u root -p{1}".format(conta, env.mysql_password))


# MYSQL - deleta o usuario e o banco de dados
def dropbase(conta=None):
    """Deletar banco de dados no servidor"""
    if not conta:
        conta = raw_input('Digite o nome do banco: ')
    if not env.mysql_password:
        env.mysql_password = raw_input('Digite a senha do ROOT do MySQL: ')
    sudo("echo DROP DATABASE {0} | mysql -u root -p{1}".format(conta, env.mysql_password))
    sudo("echo \"DROP USER '{0}'@'localhost'\" | mysql -u root -p{1}".format(conta, env.mysql_password))
    sudo("echo \"DROP USER '{0}'@'%'\" | mysql -u root -p{1}".format(conta, env.mysql_password))


# LINUX - deleta o usuario
def userdel(conta=None):
    """Deletar usuário no servidor"""
    if not conta:
        conta = raw_input('Digite o nome do usuario: ')
    log('Deletando usuário {0}'.format(conta))
    sudo('userdel -r {0}'.format(conta))


# update no servidor
def update_server():
    """Atualizando pacotes no servidor"""
    log('Atualizando pacotes')
    sudo('apt-get -y update')

# upgrade no servidor
def upgrade_server():
    """Atualizar programas no servidor"""
    log('Atualizando programas')
    sudo('apt-get -y upgrade')


def build_server():
    """Instalar build-essential e outros pacotes importantes no servidor"""
    log('Instalando build-essential e outros pacotes')
    sudo('apt-get -y install build-essential automake')
    sudo('apt-get -y install libxml2-dev libxslt-dev')
    sudo('apt-get -y install libjpeg-dev libjpeg8-dev zlib1g-dev libfreetype6 libfreetype6-dev')

    # Then, on 32-bit Ubuntu, you should run:

    # sudo ln -s /usr/lib/i386-linux-gnu/libfreetype.so /usr/lib/
    # sudo ln -s /usr/lib/i386-linux-gnu/libz.so /usr/lib/
    # sudo ln -s /usr/lib/i386-linux-gnu/libjpeg.so /usr/lib/

    # Otherwise, on 64-bit Ubuntu, you should run:

    # sudo ln -s /usr/lib/x86_64-linux-gnu/libfreetype.so /usr/lib/
    # sudo ln -s /usr/lib/x86_64-linux-gnu/libz.so /usr/lib/
    # sudo ln -s /usr/lib/x86_64-linux-gnu/libjpeg.so /usr/lib/

def python_server():
    """Instalar todos pacotes necessários do python no servidor"""
    log('Instalando todos pacotes necessários')
    sudo('sudo apt-get -y install python-imaging')
    sudo('apt-get -y install python python-dev python-setuptools python-mysqldb python-pip python-virtualenv')
    # sudo('easy_install -U distribute')


def mysql_server():
    """Instalar MySQL no servidor"""
    log('Instalando MySQL')
    sudo('apt-get -y install mysql-server libmysqlclient-dev') # nao perguntar senha do mysql pedir senha antes


def git_server():
    """Instalar git no servidor"""
    log('Instalando git')
    sudo('apt-get -y install git')

def outros_server():
    """Instalar nginx e supervisor"""
    log('Instalando nginx e supervisor')
    sudo('apt-get -y install nginx supervisor')
    sudo('apt-get -y install mercurial rubygems')
    sudo('apt-get -y install php5-fpm php5-suhosin php-apc php5-gd php5-imagick php5-curl')
    # sudo('apt-get -y install proftpd') # standalone nao perguntar
    sudo('gem install compass')

def login():
    """Acessa o servidor"""
    if chave:
        local("ssh %s -i %s" % (prod_server, env.key_filename))
    else:
        local("ssh %s" % prod_server)

def upload_public_key():
    """Faz o upload da chave ssh para o servidor"""
    log('Adicionando chave publica no servidor')
    ssh_file = '~/.ssh/id_rsa.pub'
    target_path = '~/.ssh/uploaded_key.pub'
    put(ssh_file, target_path)
    run('echo `cat ~/.ssh/uploaded_key.pub` >> ~/.ssh/authorized_keys && rm -f ~/.ssh/uploaded_key.pub')


# RESTART
def restart():
    """Reiniciar servicos no servidor"""
    log('reiniciando servicos')
    nginx_stop()
    nginx_start()
    nginx_restart()
    nginx_reload()
    supervisor_stop()
    supervisor_start()

def reboot():
    """Reinicia o servidor"""
    sudo('reboot')

# SUPERVISOR APP
def start_server():
    """Start aplicação no servidor"""
    conta = raw_input('Digite o nome da app: ')
    log('inicia aplicação')
    sudo('supervisorctl start %s' % conta)


def stop_server():
    """Stop aplicação no servidor"""
    conta = raw_input('Digite o nome da app: ')
    log('para aplicação')
    sudo('supervisorctl stop %s' % conta)


def restart_server():
    """Restart aplicação no servidor"""
    conta = raw_input('Digite o nome da app: ')
    log('reinicia aplicação')
    sudo('supervisorctl restart %s' % conta)


# SUPERVISOR
def supervisor_start():
    """Start supervisor no servidor"""
    log('start supervisor')
    sudo('/etc/init.d/supervisor start')


def supervisor_stop():
    """Stop supervisor no servidor"""
    log('stop supervisor')
    sudo('/etc/init.d/supervisor stop')


def supervisor_restart():
    """Restart supervisor no servidor"""
    log('restart supervisor')
    sudo('/etc/init.d/supervisor stop')
    sudo('/etc/init.d/supervisor start')
    # sudo('/etc/init.d/supervisor restart')


# NGINX
def nginx_start():
    """Start nginx no servidor"""
    log('start nginx')
    sudo('/etc/init.d/nginx start')


def nginx_stop():
    """Stop nginx no servidor"""
    log('stop nginx')
    sudo('/etc/init.d/nginx stop')


def nginx_restart():
    """Restart nginx no servidor"""
    log('restart nginx')
    sudo('/etc/init.d/nginx restart')


def nginx_reload():
    """Reload nginx no servidor"""
    log('reload nginx')
    sudo('/etc/init.d/nginx reload')


# --------------------------------------------------------
# LOCAL
# --------------------------------------------------------

# cria projeto local
def newproject():
    """ Criar novo projeto local """
    log('Criando novo projeto')
    log('Cria a conta no bitbucket com o nome do projeto vázio que o script se encarregará do resto')

    conta = raw_input('Digite o nome do projeto: ')

    local('echo "clonando projeto %s"' % bitbucket_repository)
    local('git clone {0} {1}{2}'.format(bitbucket_repository, folder_project_local, conta))
    local('cd {0}{1}'.format(folder_project_local, conta))
    local('mkvirtualenv {0}'.format(conta))
    local('setvirtualenvproject')
    local('pip install -r requirements.txt')
    local('rm -rf {0}{1}/.git'.format(folder_project_local, conta))
    local('rm -rf README.md')
    local('git init')
    local('git remote add origin git@bitbucket.org:{0}/{1}.git'.format(bitbucket_user, conta))

# configura uma maquina local ubuntu
def newdev():
    """Configura uma maquina local Ubuntu para trabalhar python/django"""
    log('Configura uma computador Ubuntu para trabalhar python/django')
    update_local()
    upgrade_local()

    # pacotes
    build_local()
    python_local()
    mysql_local()
    git_local()

    # atualizando
    update_local()
    upgrade_local()

# update no local
def update_local():
    """Atualizando pacotes"""
    log('Atualizando pacotes')
    local('sudo apt-get update')

# upgrade no local
def upgrade_local():
    """Atualizando programas"""
    log('Atualizando programas')
    local('sudo apt-get upgrade')


def build_local():
    """Instalar build-essential"""
    log('instalando build-essential gcc++')
    local('sudo apt-get -y install build-essential automake')
    local('sudo apt-get -y install libxml2-dev libxslt-dev')
    local('sudo apt-get -y install libjpeg-dev libjpeg8-dev zlib1g-dev libfreetype6 libfreetype6-dev')
    local('sudo apt-get -y install terminator')

def python_local():
    """Instalando todos pacotes necessários"""
    log('Instalando todos pacotes necessários')
    local('sudo apt-get -y install python python-dev python-setuptools python-mysqldb python-pip python-virtualenv')
    local('sudo pip install -U distribute')
    local('sudo pip install virtualenvwrapper')
    local('sudo apt-get install python-imaging')
    # local('cp ~/.bashrc ~/.bashrc_bkp')
    # local('cat ~/.bashrc inc/bashrc > ~/.bashrc')
    # local('source ~/.bashrc')

def mysql_local():
    """Instalando MySQL"""
    log('Instalando MySQL')
    local('sudo apt-get -y install mysql-server libmysqlclient-dev')


def git_local():
    """Instalando git"""
    log('Instalando git')
    local('sudo apt-get -y install git')


# --------------------------------------------------------
# GLOBAL
# --------------------------------------------------------

# gera senha
def gera_senha(tamanho=12):
    """Gera uma senha - parametro tamanho"""
    from random import choice
    caracters = '0123456789abcdefghijlmnopqrstuwvxzkABCDEFGHIJLMNOPQRSTUWVXZK_#'
    senha = ''
    for char in xrange(tamanho):
        senha += choice(caracters)
    return senha


def log(message):
    print """
================================================================================
%s
================================================================================
    """ % message
