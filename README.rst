=============================
python-takserver-api
=============================

Async Python 3 library wrapping the TAK Server HTTP API. All network I/O uses
``asyncio`` + ``aiohttp`` with certificate-based mutual TLS authentication.

Documentation lives in the project wiki:
https://github.com/sgofferj/python-takserver-api.wiki


API surface
-----------

The library is organized into a ``Server`` class with sub-api accessors,
each wrapping one tag of the live OpenAPI spec (``tests/openapispec.json``).
Currently covered classes:

.. list-table:: Covered API classes
   :widths: 28 15 20 40
   :header-rows: 1

   * - Class
     - Accessor
     - Coverage
     - Status
   * - ``HomeApi``
     - ``server.home``
     - 3 of 4 spec operations
     - Complete, incl. helpers
   * - ``MissionApi``
     - ``server.mission``
     - 69 of 112 spec operations
     - Complete, incl. helpers
   * - ``UserAccountManagementApi``
     - ``server.user``
     - 10 of 10 spec operations
     - Complete, incl. helpers
   * - ``GroupApi``
     - ``server.groups``
     - 10 of 10 spec operations
     - Complete, incl. helpers
   * - ``DataFeedApi``
     - ``server.datafeeds``
     - 11 of 11 spec operations
     - Complete, incl. helpers
   * - ``CertManagerApi``
     - ``server.certs``
     - 10 of 15 spec operations
     - Complete; 5 ops broken server-side, not wrapped

**Home API** — ``server.home``

* ``is_admin()`` · ``get_home()`` · ``get_user_roles()``
* Helpers: ``has_role()`` · ``server_version()``

**User Account Management API** — ``server.user``

* Users: ``get_all_users()`` · ``user_exists()`` ·
  ``create_or_update_file_user()`` · ``change_user_password()`` ·
  ``delete_user()`` · ``create_file_users_in_bulk()``
* Groups: ``get_all_group_names()`` · ``group_exists()`` ·
  ``get_users_in_group()`` · ``update_users_for_group()`` ·
  ``get_groups_for_user()`` · ``update_groups_for_user()``

**Group API** — ``server.groups`` *(channel subscriptions)*

* Catalog & lookup: ``get_all_groups()`` · ``get_group()`` ·
  ``get_channels()`` · ``channel_exists()``
* Subscriptions: ``set_active_groups()`` · ``set_active_groups_bits()`` ·
  ``set_active_groups_force()`` · ``wait_for_group_update()``
* Helpers: ``get_active_groups()`` · ``subscribe()`` /
  ``subscribe_many()`` · ``unsubscribe()`` / ``unsubscribe_many()`` ·
  ``is_subscribed()`` · ``wait_for_group_update_until()``
* LDAP: ``get_ldap_groups()`` · ``get_ldap_group_members()``
* Note: subscription helpers need the caller's username — pass
  ``Server(..., username=...)`` (the certificate CN) or give an explicit
  ``username=`` argument. See the Groups-API wiki page for scope notes
  (entitlements vs. available channels vs. active subscriptions).

**Data Feed API** — ``server.datafeeds``

* Catalog: ``get_data_feeds()`` · ``get_data_feeds_in_bbox()`` ·
  ``get_data_feeds_in_polygon()``
* Predicate feeds: ``build_predicate_feed()`` ·
  ``create_predicate_data_feed()`` · ``update_predicate_data_feed()`` ·
  ``delete_predicate_data_feed()`` · ``get_predicate_data_feed()``
* Stats & content: ``get_stats()`` · ``get_stats_for_feed()`` ·
  ``get_existing_cot_types()`` · ``get_cots_by_cot_type()``
* See the Data-Feeds-API wiki page for the filter-groups access-lockout
  trap.

**Cert Manager API** — ``server.certs`` *(admin only)*

* Listing: ``get_certificates(username=None)`` ·
  ``get_active_certificates()`` · ``get_expired_certificates()`` ·
  ``get_replaced_certificates()`` · ``get_revoked_certificates()``
* Records: ``get_certificate()`` · ``download_certificate()``
* Mutations: ``revoke_certificates()`` · ``delete_certificates()`` ·
  ``delete_certificate()``
* The user-side TLS enrollment endpoints are not wrapped (server answers
  403 even to admins); see the Cert-Manager-API wiki page.

**Mission API** — ``server.mission``

* All name-based mission endpoints of the live spec: lifecycle
  (create/delete/copy/archive/expiration/parent), content, content
  keywords, external data, invitations, passwords, tokens, layers,
  map layers, feeds, logs and subscriptions
* Global endpoints: mission count/names, paged list,
  all-invitations/logs/subscriptions
* Extras: ``build_mission_package()`` / ``add_mission_package()`` and the
  single-keyword content helpers ``delete_content_keyword_by_hash()`` /
  ``delete_content_keyword_by_uid()``

Endpoints that are proven not to work on the reference server are
deliberately NOT wrapped (e.g. home-api ``getVer`` / ``GET /Marti/api/ver``
returns HTTP 500); see the wiki "Not implemented" sections.

The user API wrappers always send all three group-list fields (``groupList``,
``groupListIN``, ``groupListOUT``) - the reference server answers HTTP 500
when any is omitted. Groups are implicit: they appear when a user carries
them and disappear when no user has them. See the wiki for details.


Tested TAK server version
-------------------------

The current state of this library is tested against a real TAK server running
**5.7-RELEASE-43-HEAD** (reportable at runtime via
``await server.home.server_version()``, verified 2026-08-10).

The API specification used as the development baseline is
``tests/openapispec.json``, pulled live from the test server's
``/v3/api-docs`` endpoint.

Live integration tests
----------------------

The live tests in ``live_tests/`` are never part of CI; they run only against
the developer's own TAK server. Configure that server in an untracked ``.env``
file in the repository root (``.env`` is gitignored)::

    TAK_LIVE_HOST=tak.example.com
    TAK_LIVE_CERT=path/to/client.pem
    TAK_LIVE_KEY=path/to/client.key

Without a complete ``.env`` the live tests skip automatically. Never commit
the server address or any credentials.


Docker
------

For more controlled deployments and to get rid of "works on my computer" -syndrome, we always
make sure our software works under docker.

It's also a quick way to get started with a standard development environment.

SSH agent forwarding
^^^^^^^^^^^^^^^^^^^^

We need buildkit_::

    export DOCKER_BUILDKIT=1

.. _buildkit: https://docs.docker.com/develop/develop-images/build_enhancements/

And also the exact way for forwarding agent to running instance is different on OSX::

    export DOCKER_SSHAGENT="-v /run/host-services/ssh-auth.sock:/run/host-services/ssh-auth.sock -e SSH_AUTH_SOCK=/run/host-services/ssh-auth.sock"

and Linux::

    export DOCKER_SSHAGENT="-v $SSH_AUTH_SOCK:$SSH_AUTH_SOCK -e SSH_AUTH_SOCK"

Creating a development container
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Build image, create container and start it::

    docker build --ssh default --target devel_shell -t python_takserver_api:devel_shell .
    docker create --name python_takserver_api_devel -v "$(pwd):/app" -it $(echo $DOCKER_SSHAGENT) python_takserver_api:devel_shell
    docker start -i python_takserver_api_devel

pre-commit considerations
^^^^^^^^^^^^^^^^^^^^^^^^^

If working in Docker instead of native env you need to run the pre-commit checks in docker too::

    docker exec -i python_takserver_api_devel /bin/bash -c "pre-commit install --install-hooks"
    docker exec -i python_takserver_api_devel /bin/bash -c "pre-commit run --all-files"

You need to have the container running, see above. Or alternatively use the docker run syntax but using
the running container is faster::

    docker run --rm -it -v "$(pwd):/app" python_takserver_api:devel_shell -c "pre-commit run --all-files"

Test suite
^^^^^^^^^^

You can use the devel shell to run py.test when doing development, for CI use
the "tox" target in the Dockerfile::

    docker build --ssh default --target tox -t python_takserver_api:tox .
    docker run --rm -it -v "$(pwd):/app" $(echo $DOCKER_SSHAGENT) python_takserver_api:tox

Production docker
^^^^^^^^^^^^^^^^^

There's a "production" target as well for running the application, remember to change that
architecture tag to arm64 if building on ARM::

    docker build --ssh default --target production -t python_takserver_api:latest .
    docker run -it --name python_takserver_api python_takserver_api:amd64-latest

Alpine considerations
^^^^^^^^^^^^^^^^^^^^^

Alpine images are much more lightweight than Debian/Ubuntu ones so they are preferred where possible.
There are a few potential issues however:

  - Compiled extensions not available as wheels. This is mostly mitigated by our own wheel builder.
  - Compiled extensions not compiling under Alpine. Alpine does not have certain nonstandard extensions to libc
    enabled by default, poorly written extensions will fail to compile because they depend on these extensions
    and do not explicitly request them to be enabled.
  - Poetry lockfile might need to be updated by running poetry inside Alpine Docker (use devel_shell above)


Development
-----------

TLDR:

- Create and activate a Python 3.11+ virtualenv (assuming virtualenvwrapper)::

    mkvirtualenv -p $(which python3.13) my_virtualenv

- install Poetry: https://python-poetry.org/docs/#installation
- Install project deps and pre-commit hooks::

    poetry install
    pre-commit install --install-hooks
    pre-commit run --all-files

If you get weird errors about missing packages from pre-commit try running it with "poetry run pre-commit".

- Branch workflow: feature work goes on ``feat/<topic>`` branches and is
  merged into ``main`` (via pull request or direct merge); keep the default
  branch ``main`` free of direct commits. Wiki doc changes ship on
  ``docs/<topic>`` branches and must be merged into the wiki's ``master``
  (the wiki UI only renders ``master``; see AGENTS.md).
- Ready to go.

Remember to activate your virtualenv whenever working on the repo, this is needed
because pylint and mypy pre-commit hooks use the "system" python for now (because reasons).

Running "pre-commit run --all-files" and "py.test -v" regularly during development and
especially before committing will save you some headache.
