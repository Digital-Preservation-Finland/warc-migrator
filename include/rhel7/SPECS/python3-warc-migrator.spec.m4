# vim:ft=spec

%define file_prefix M4_FILE_PREFIX
%define file_ext M4_FILE_EXT

%define file_version M4_FILE_VERSION
%define file_release_tag %{nil}M4_FILE_RELEASE_TAG
%define file_release_number M4_FILE_RELEASE_NUMBER
%define file_build_number M4_FILE_BUILD_NUMBER
%define file_commit_ref M4_FILE_COMMIT_REF

Name:           python3-warc-migrator
Version:        %{file_version}
Release:        %{file_release_number}%{file_release_tag}.%{file_build_number}.git%{file_commit_ref}%{?dist}
Summary:        WARC migration tool
Group:          Applications/Archiving
License:        LGPLv3+
URL:            https://digitalpreservation.fi
Source0:        %{file_prefix}-v%{file_version}%{?file_release_tag}-%{file_build_number}-g%{file_commit_ref}.%{file_ext}
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch

Requires:       python3 python36-click python36-lxml python36-six
Requires:       python3-warcio python3-warc-tools python3-xml-helpers
BuildRequires:  python3-setuptools python36-pytest

%description
The tool migrates ARC 1.0/1.1 and WARC 0.17/0.18 to WARC 1.0 and validates it.

%prep
find %{_sourcedir}
%setup -n %{file_prefix}-v%{file_version}%{?file_release_tag}-%{file_build_number}-g%{file_commit_ref}

%build
%{__python3} setup.py build

%pre

%install
%{__python3} setup.py install -O1 --root $RPM_BUILD_ROOT --record=INSTALLED_FILES

%post

%clean

%files -f INSTALLED_FILES
%defattr(-,root,root,-)

# TODO: For now changelog must be last, because it is generated automatically
# from git log command. Appending should be fixed to happen only after %changelog macro
%changelog
