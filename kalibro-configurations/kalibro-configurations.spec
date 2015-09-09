Name: kalibro-configurations		
Version: 1.0.0.backport	
Release: 2%{?dist}
Summary: Mezuro metrics management backend 	
Group: Development/Tools
License: AGPLv3	
URL: https://github.com/mezuro/kalibro_configurations		
Source0: %{name}-%{version}.tar.gz	
BuildRoot:	%{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch: noarch
BuildRequires: kalibro-configurations-deps	
Requires: kalibro-configurations-deps, rubygem-bundler	

%description

%prep
%setup -q

%build
ln -sf /usr/lib/kalibro_configurations/Gemfile .
ln -sf /usr/lib/kalibro_configurations/Gemfile.lock .
ln -sf /usr/lib/kalibro_configurations/.bundle .
ln -sfT /usr/lib/kalibro_configurations/vendor/bundle vendor/bundle
rm -f Gemfile Gemfile.lock .bundle vendor/bundle 
rm -rf tmp log

%install
mkdir -p %{buildroot}/usr/lib/kalibro-configurations
cp -r * %{buildroot}/usr/lib/kalibro-configurations
rm -rf %{buildroot}/usr/lib/kalibro-configurations/log
ln -sfT /var/log/kalibro-configurations %{buildroot}/usr/lib/kalibro-configurations/log
ln -sfT /etc/kalibro-configurations/database.yml %{buildroot}/usr/lib/kalibro-configurations/config/database.yml
ln -sfT /etc/kalibro-configurations/secrets.yml %{buildroot}/usr/lib/kalibro-configurations/config/secrets.yml

mkdir -p %{buildroot}/lib/systemd/system
cat > %{buildroot}/lib/systemd/system/kalibro_configurations.service <<EOF
[Unit]
Description=kalibro_configurations 
After=network.target

[Service]
Type=simple
EnvironmentFile=-/etc/sysconfig/kalibro_configurations
User=kalibro_configurations
WorkingDirectory=/usr/lib/kalibro-configurations
ExecStart=/usr/bin/env bundle exec rails s -p 8083 -e production
[Install]
WantedBy=multi-user.target
EOF

mkdir -p %{buildroot}/etc/kalibro-configurations
cat > %{buildroot}/etc/kalibro-configurations/database.yml <<EOF
production:
  adapter: postgresql
  encoding: unicode
  database: kalibro_configurations_production
  pool: 10
  username: kalibro_configurations
  password:
EOF

cat > %{buildroot}/etc/kalibro-configurations/secrets.yml <<EOF
production:
  secret_key_base: $(bundle exec rake secret)
EOF

#FIXME HACK, REMOVE LATER
sed -i -e "s/require.*database_cleaner/# &/" %{buildroot}/usr/lib/kalibro-configurations/app/controllers/tests_controller.rb

%post
groupadd kalibro_configurations || true
if ! id kalibro_configurations; then
  adduser kalibro_configurations --system -g kalibro_configurations --shell /bin/sh --home-dir /usr/lib/kalibro-configurations
fi
mkdir -p /var/log/kalibro-configurations 
chown -R kalibro_configurations:kalibro_configurations /var/log/kalibro-configurations
chown -R kalibro_configurations:kalibro_configurations /usr/lib/kalibro-configurations
if [ -x /usr/bin/psql ]; then
  if [ `systemctl is-active postgresql`!="active" ]; then
    postgresql-setup initdb || true
    systemctl start postgresql
  fi
  if [ "$(sudo -u postgres -i psql --quiet --tuples-only -c "select count(*) from pg_user where usename = 'kalibro_configurations';")" -eq 0 ]; then
    # create user
    sudo -u postgres -i createuser kalibro_configurations
  fi

  if [ "$(sudo -u postgres -i psql --quiet --tuples-only -c "select count(1) from pg_database where datname = 'kalibro_configurations_production';")" -eq 0 ]; then
    # create database
    sudo -u postgres -i createdb --owner=kalibro_configurations kalibro_configurations_production
  fi

  cd /usr/lib/kalibro-configurations/
  su kalibro_configurations -c "RAILS_ENV=production bundle exec rake db:migrate"
  if [ $1 -eq 1 ]; then
    su kalibro_configurations -c "RAILS_ENV=production bundle exec rake db:seed"
  fi
fi

if [ $1 -gt 1 ]; then
  echo 'Restarting kalibro_configurations'
  systemctl daemon-reload
  systemctl try-restart kalibro_configurations
fi

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc
/usr/lib/kalibro-configurations
/lib/systemd/system/kalibro_configurations.service
%config(noreplace) /etc/kalibro-configurations/database.yml
%config(noreplace) /etc/kalibro-configurations/secrets.yml

%changelog
