import os
import textwrap
from pathlib import Path

import pytest

import prefect.context
import prefect.settings
from prefect.settings import (
    DEFAULT_PROFILES_PATH,
    PREFECT_API_KEY,
    PREFECT_API_URL,
    PREFECT_DEBUG_MODE,
    PREFECT_HOME,
    PREFECT_LOGGING_EXTRA_LOGGERS,
    PREFECT_LOGGING_LEVEL,
    PREFECT_ORION_API_HOST,
    PREFECT_ORION_API_PORT,
    PREFECT_ORION_DATABASE_ECHO,
    PREFECT_ORION_UI_API_URL,
    PREFECT_PROFILES_PATH,
    PREFECT_TEST_MODE,
    PREFECT_TEST_SETTING,
    SETTING_VARIABLES,
    Profile,
    ProfilesCollection,
    Settings,
    get_current_settings,
    load_profile,
    load_profiles,
    save_profiles,
    temporary_settings,
)


class TestSettingsClass:
    def test_settings_copy_with_update_does_not_mark_unset_as_set(self):
        settings = get_current_settings()
        set_keys = set(settings.dict(exclude_unset=True).keys())
        new_settings = settings.copy_with_update()
        new_set_keys = set(new_settings.dict(exclude_unset=True).keys())
        assert new_set_keys == set_keys

        new_settings = settings.copy_with_update(updates={PREFECT_API_KEY: "TEST"})
        new_set_keys = set(new_settings.dict(exclude_unset=True).keys())
        # Only the API key setting should be set
        assert new_set_keys - set_keys == {"PREFECT_API_KEY"}

    def test_settings_copy_with_update(self):
        settings = get_current_settings()
        assert settings.value_of(PREFECT_TEST_MODE) is True

        with temporary_settings(restore_defaults={PREFECT_API_KEY}):
            new_settings = settings.copy_with_update(
                updates={PREFECT_LOGGING_LEVEL: "ERROR"},
                set_defaults={PREFECT_TEST_MODE: False, PREFECT_API_KEY: "TEST"},
            )
            assert (
                new_settings.value_of(PREFECT_TEST_MODE) is True
            ), "Not changed, existing value was not default"
            assert (
                new_settings.value_of(PREFECT_API_KEY) == "TEST"
            ), "Changed, existing value was default"
            assert new_settings.value_of(PREFECT_LOGGING_LEVEL) == "ERROR"

    def test_settings_loads_environment_variables_at_instantiation(self, monkeypatch):
        assert PREFECT_TEST_MODE.value() is True

        monkeypatch.setenv("PREFECT_TEST_MODE", "0")
        new_settings = Settings()
        assert PREFECT_TEST_MODE.value_from(new_settings) is False

    def test_settings_to_environment_includes_all_settings_with_non_null_values(self):
        settings = Settings()
        assert set(settings.to_environment_variables().keys()) == {
            key for key in SETTING_VARIABLES if getattr(settings, key) is not None
        }

    def test_settings_to_environment_casts_to_strings(self):
        assert (
            Settings(PREFECT_ORION_API_PORT=3000).to_environment_variables()[
                "PREFECT_ORION_API_PORT"
            ]
            == "3000"
        )

    def test_settings_to_environment_respects_includes(self):
        include = [PREFECT_ORION_API_PORT]

        assert Settings(PREFECT_ORION_API_PORT=3000).to_environment_variables(
            include=include
        ) == {"PREFECT_ORION_API_PORT": "3000"}

        assert include == [PREFECT_ORION_API_PORT], "Passed list should not be mutated"

    def test_settings_to_environment_respects_includes(self):
        include = [PREFECT_ORION_API_PORT]

        assert Settings(PREFECT_ORION_API_PORT=3000).to_environment_variables(
            include=include
        ) == {"PREFECT_ORION_API_PORT": "3000"}

        assert include == [PREFECT_ORION_API_PORT], "Passed list should not be mutated"

    def test_settings_to_environment_exclude_unset_empty_if_none_set(self, monkeypatch):
        for key in SETTING_VARIABLES:
            monkeypatch.delenv(key, raising=False)

        assert Settings().to_environment_variables(exclude_unset=True) == {}

    def test_settings_to_environment_exclude_unset_only_includes_set(self, monkeypatch):
        for key in SETTING_VARIABLES:
            monkeypatch.delenv(key, raising=False)

        assert Settings(
            PREFECT_DEBUG_MODE=True, PREFECT_API_KEY="Hello"
        ).to_environment_variables(exclude_unset=True) == {
            "PREFECT_DEBUG_MODE": "True",
            "PREFECT_API_KEY": "Hello",
        }

    def test_settings_to_environment_exclude_unset_only_includes_set_even_if_included(
        self, monkeypatch
    ):
        for key in SETTING_VARIABLES:
            monkeypatch.delenv(key, raising=False)

        include = [PREFECT_HOME, PREFECT_DEBUG_MODE, PREFECT_API_KEY]

        assert Settings(
            PREFECT_DEBUG_MODE=True, PREFECT_API_KEY="Hello"
        ).to_environment_variables(exclude_unset=True, include=include) == {
            "PREFECT_DEBUG_MODE": "True",
            "PREFECT_API_KEY": "Hello",
        }

        assert include == [
            PREFECT_HOME,
            PREFECT_DEBUG_MODE,
            PREFECT_API_KEY,
        ], "Passed list should not be mutated"

    @pytest.mark.parametrize("exclude_unset", [True, False])
    def test_settings_to_environment_roundtrip(self, exclude_unset, monkeypatch):
        settings = Settings()
        variables = settings.to_environment_variables(exclude_unset=exclude_unset)
        for key, value in variables.items():
            monkeypatch.setenv(key, value)
        new_settings = Settings()
        assert settings.dict() == new_settings.dict()

    def test_settings_to_environment_does_not_use_value_callback(sel):
        settings = Settings(PREFECT_ORION_UI_API_URL=None)
        # This would be cast to a non-null value if the value callback was used when
        # generating the environment variables
        assert "PREFECT_ORION_UI_API_URL" not in settings.to_environment_variables()


class TestSettingAccess:
    def test_get_value_root_setting(self):
        with temporary_settings(
            updates={PREFECT_API_URL: "test"}
        ):  # Set a value so its not null
            value = prefect.settings.PREFECT_API_URL.value()
            value_of = get_current_settings().value_of(PREFECT_API_URL)
            value_from = PREFECT_API_URL.value_from(get_current_settings())
            assert value == value_of == value_from == "test"

    def test_get_value_nested_setting(self):
        value = prefect.settings.PREFECT_LOGGING_LEVEL.value()
        value_of = get_current_settings().value_of(PREFECT_LOGGING_LEVEL)
        value_from = PREFECT_LOGGING_LEVEL.value_from(get_current_settings())
        assert value == value_of == value_from

    def test_test_mode_access(self):
        assert PREFECT_TEST_MODE.value() is True

    def test_settings_in_truthy_statements_use_value(self):
        if PREFECT_TEST_MODE:
            assert True, "Treated as truth"
        else:
            assert False, "Not treated as truth"

        with temporary_settings(updates={PREFECT_TEST_MODE: False}):
            if not PREFECT_TEST_MODE:
                assert True, "Treated as truth"
            else:
                assert False, "Not treated as truth"

        # Test with a non-boolean setting

        if PREFECT_LOGGING_LEVEL:
            assert True, "Treated as truth"
        else:
            assert False, "Not treated as truth"

        with temporary_settings(updates={PREFECT_LOGGING_LEVEL: ""}):
            if not PREFECT_LOGGING_LEVEL:
                assert True, "Treated as truth"
            else:
                assert False, "Not treated as truth"

    def test_ui_api_url_from_api_url(self):
        with temporary_settings({PREFECT_API_URL: "http://test/api"}):
            assert PREFECT_ORION_UI_API_URL.value() == "http://test/api"

    def test_ui_api_url_from_orion_host_and_port(self):
        with temporary_settings(
            {PREFECT_ORION_API_HOST: "test", PREFECT_ORION_API_PORT: "1111"}
        ):
            assert PREFECT_ORION_UI_API_URL.value() == "http://test:1111/api"

    def test_ui_api_url_from_defaults(self):
        assert PREFECT_ORION_UI_API_URL.value() == "http://127.0.0.1:4200/api"

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("foo", ["foo"]),
            ("foo,bar", ["foo", "bar"]),
            ("foo, bar, foobar ", ["foo", "bar", "foobar"]),
        ],
    )
    def test_extra_loggers(self, value, expected):
        settings = Settings(PREFECT_LOGGING_EXTRA_LOGGERS=value)
        assert PREFECT_LOGGING_EXTRA_LOGGERS.value_from(settings) == expected

    def test_prefect_home_expands_tilde_in_path(self):
        settings = Settings(PREFECT_HOME="~/test")
        assert PREFECT_HOME.value_from(settings) == Path("~/test").expanduser()


class TestTemporarySettings:
    def test_temporary_settings(self):
        assert PREFECT_TEST_MODE.value() is True
        with temporary_settings(updates={PREFECT_TEST_MODE: False}) as new_settings:
            assert (
                PREFECT_TEST_MODE.value_from(new_settings) is False
            ), "Yields the new settings"
            assert PREFECT_TEST_MODE.value() is False

        assert PREFECT_TEST_MODE.value() is True

    def test_temporary_settings_does_not_mark_unset_as_set(self):
        settings = get_current_settings()
        set_keys = set(settings.dict(exclude_unset=True).keys())
        with temporary_settings() as new_settings:
            pass
        new_set_keys = set(new_settings.dict(exclude_unset=True).keys())
        assert new_set_keys == set_keys

    def test_temporary_settings_can_restore_to_defaults_values(self):
        with temporary_settings(updates={PREFECT_TEST_SETTING: "FOO"}):
            with temporary_settings(restore_defaults={PREFECT_TEST_SETTING}):
                assert (
                    PREFECT_TEST_SETTING.value() == PREFECT_TEST_SETTING.field.default
                )

    def test_temporary_settings_restores_on_error(self):
        assert PREFECT_TEST_MODE.value() is True

        with pytest.raises(ValueError):
            with temporary_settings(updates={PREFECT_TEST_MODE: False}):
                raise ValueError()

        assert os.environ["PREFECT_TEST_MODE"] == "1", "Does not alter os environ."
        assert PREFECT_TEST_MODE.value() is True


class TestProfilesReadWrite:
    @pytest.fixture(autouse=True)
    def temporary_profiles_path(self, tmp_path):
        path = tmp_path / "profiles.toml"
        with temporary_settings(updates={PREFECT_PROFILES_PATH: path}):
            yield path

    def test_load_profiles_no_profiles_file(self):
        assert load_profiles()

    def test_load_profiles_missing_default(self, temporary_profiles_path):
        temporary_profiles_path.write_text(
            textwrap.dedent(
                """
                [profiles.foo]
                PREFECT_API_KEY = "bar"
                """
            )
        )
        assert load_profiles()["foo"].settings == {PREFECT_API_KEY: "bar"}
        assert isinstance(load_profiles()["default"].settings, dict)

    def test_load_profiles_with_default(self, temporary_profiles_path):
        temporary_profiles_path.write_text(
            textwrap.dedent(
                """
                [profiles.default]
                PREFECT_API_KEY = "foo"

                [profiles.bar]
                PREFECT_API_KEY = "bar"
                """
            )
        )
        assert load_profiles() == ProfilesCollection(
            profiles=[
                Profile(
                    name="default",
                    settings={PREFECT_API_KEY: "foo"},
                    source=temporary_profiles_path,
                ),
                Profile(
                    name="bar",
                    settings={PREFECT_API_KEY: "bar"},
                    source=temporary_profiles_path,
                ),
            ],
            active="default",
        )

    def test_save_profiles_does_not_include_default(self, temporary_profiles_path):
        """
        Including the default has a tendency to bake in settings the user may not want, and
        can prevent them from gaining new defaults.
        """
        save_profiles(ProfilesCollection(active=None, profiles=[]))
        assert "profiles.default" not in temporary_profiles_path.read_text()

    def test_save_profiles_additional_profiles(self, temporary_profiles_path):
        save_profiles(
            ProfilesCollection(
                profiles=[
                    Profile(
                        name="foo",
                        settings={PREFECT_API_KEY: 1},
                        source=temporary_profiles_path,
                    ),
                    Profile(
                        name="bar",
                        settings={PREFECT_API_KEY: 2},
                        source=temporary_profiles_path,
                    ),
                ],
                active=None,
            )
        )
        assert (
            temporary_profiles_path.read_text()
            == textwrap.dedent(
                """
                [profiles.foo]
                PREFECT_API_KEY = 1

                [profiles.bar]
                PREFECT_API_KEY = 2
                """
            ).lstrip()
        )

    def test_load_profile_default(self):
        assert load_profile("default") == Profile(
            name="default", settings={}, source=DEFAULT_PROFILES_PATH
        )

    def test_load_profile_missing(self):
        with pytest.raises(ValueError, match="Profile 'foo' not found."):
            load_profile("foo")

    def test_load_profile(self, temporary_profiles_path):
        temporary_profiles_path.write_text(
            textwrap.dedent(
                """
                [profiles.foo]
                PREFECT_API_KEY = "bar"
                PREFECT_DEBUG_MODE = 1
                """
            )
        )
        assert load_profile("foo") == Profile(
            name="foo",
            settings={
                PREFECT_API_KEY: "bar",
                PREFECT_DEBUG_MODE: 1,
            },
            source=temporary_profiles_path,
        )

    def test_load_profile_does_not_allow_nested_data(self, temporary_profiles_path):
        temporary_profiles_path.write_text(
            textwrap.dedent(
                """
                [profiles.foo]
                PREFECT_API_KEY = "bar"

                [profiles.foo.nested]
                """
            )
        )
        with pytest.raises(ValueError, match="Unknown setting.*'nested'"):
            load_profile("foo")

    def test_load_profile_with_invalid_key(self, temporary_profiles_path):
        temporary_profiles_path.write_text(
            textwrap.dedent(
                """
                [profiles.foo]
                test = "unknown-key"
                """
            )
        )
        with pytest.raises(ValueError, match="Unknown setting.*'test'"):
            load_profile("foo")


class TestProfilesCollection:
    def test_update_profile_adds_key(self):
        profiles = ProfilesCollection(profiles=[Profile(name="test", settings={})])
        profiles.update_profile(name="test", settings={PREFECT_API_URL: "hello"})
        assert profiles["test"].settings == {PREFECT_API_URL: "hello"}

    def test_update_profile_updates_key(self):
        profiles = ProfilesCollection(profiles=[Profile(name="test", settings={})])
        profiles.update_profile(name="test", settings={PREFECT_API_URL: "hello"})
        assert profiles["test"].settings == {PREFECT_API_URL: "hello"}
        profiles.update_profile(name="test", settings={PREFECT_API_URL: "goodbye"})
        assert profiles["test"].settings == {PREFECT_API_URL: "goodbye"}

    def test_update_profile_removes_key(self):
        profiles = ProfilesCollection(profiles=[Profile(name="test", settings={})])
        profiles.update_profile(name="test", settings={PREFECT_API_URL: "hello"})
        assert profiles["test"].settings == {PREFECT_API_URL: "hello"}
        profiles.update_profile(name="test", settings={PREFECT_API_URL: None})
        assert profiles["test"].settings == {}

    def test_update_profile_mixed_add_and_update(self):
        profiles = ProfilesCollection(profiles=[Profile(name="test", settings={})])
        profiles.update_profile(name="test", settings={PREFECT_API_URL: "hello"})
        assert profiles["test"].settings == {PREFECT_API_URL: "hello"}
        profiles.update_profile(
            name="test",
            settings={PREFECT_API_URL: "goodbye", PREFECT_LOGGING_LEVEL: "DEBUG"},
        )
        assert profiles["test"].settings == {
            PREFECT_API_URL: "goodbye",
            PREFECT_LOGGING_LEVEL: "DEBUG",
        }

    def test_update_profile_retains_existing_keys(self):
        profiles = ProfilesCollection(profiles=[Profile(name="test", settings={})])
        profiles.update_profile(name="test", settings={PREFECT_API_URL: "hello"})
        assert profiles["test"].settings == {PREFECT_API_URL: "hello"}
        profiles.update_profile(name="test", settings={PREFECT_LOGGING_LEVEL: "DEBUG"})
        assert profiles["test"].settings == {
            PREFECT_API_URL: "hello",
            PREFECT_LOGGING_LEVEL: "DEBUG",
        }
