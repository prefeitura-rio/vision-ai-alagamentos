# -*- coding: utf-8 -*-
from os import getenv
from typing import List

from infisical import InfisicalClient
from loguru import logger


def getenv_or_action(
    env_name: str, *, action: str = "raise", default: str = None
) -> str:
    """Get an environment variable or raise an exception.

    Args:
        env_name (str): The name of the environment variable.
        action (str, optional): The action to take if the environment variable is not set.
            Defaults to "raise".
        default (str, optional): The default value to return if the environment variable is not set.
            Defaults to None.

    Raises:
        ValueError: If the action is not one of "raise", "warn", or "ignore".

    Returns:
        str: The value of the environment variable, or the default value if the environment variable
            is not set.
    """
    if action not in ["raise", "warn", "ignore"]:
        raise ValueError("action must be one of 'raise', 'warn', or 'ignore'")

    value = getenv(env_name, default)
    if value is None:
        if action == "raise":
            raise EnvironmentError(f"Environment variable {env_name} is not set.")
        elif action == "warn":
            logger.warning(f"Warning: Environment variable {env_name} is not set.")
    return value


def getenv_list_or_action(
    env_name: str, *, action: str = "raise", default: str = None
) -> List[str]:
    """Get an environment variable or raise an exception.

    Args:
        env_name (str): The name of the environment variable.
        action (str, optional): The action to take if the environment variable is not set.
            Defaults to "raise".
        default (str, optional): The default value to return if the environment variable is not set.
            Defaults to None.

    Raises:
        ValueError: If the action is not one of "raise", "warn", or "ignore".

    Returns:
        str: The value of the environment variable, or the default value if the environment variable
            is not set.
    """
    value = getenv_or_action(env_name, action=action, default=default)
    if value is not None:
        if isinstance(value, str):
            return value.split(",")
        elif isinstance(value, list):
            return value
        else:
            raise TypeError("value must be a string or a list")
    return []


def mask_string(string: str, *, mask: str = "*") -> str:
    """This function masks a string with a given mask.
    It will show a few first and last characters of the string, and mask the rest.
    The number of characters shown is the length of the string divided by 4, rounded down.

    Args:
        string (str): The string to be masked.
        mask (str, optional): The mask to use. Defaults to "*".

    Returns:
        str: The masked string.
    """
    length = len(string)
    number_of_characters_to_show = int(length / 4)
    if number_of_characters_to_show % 2 == 0:
        number_of_starting_characters_to_show = int(number_of_characters_to_show / 2)
        number_of_ending_characters_to_show = number_of_starting_characters_to_show
    else:
        number_of_starting_characters_to_show = int(number_of_characters_to_show / 2)
        number_of_ending_characters_to_show = number_of_starting_characters_to_show + 1
    first_characters = string[:number_of_starting_characters_to_show]
    last_characters = string[-number_of_ending_characters_to_show:]
    return f"{first_characters}{mask * (length - number_of_characters_to_show * 2)}{last_characters}"  # noqa


def inject_environment_variables(environment: str):
    """Inject environment variables from Infisical."""
    site_url = getenv_or_action("INFISICAL_ADDRESS", action="raise")
    token = getenv_or_action("INFISICAL_TOKEN", action="raise")
    infisical_client = InfisicalClient(
        token=token,
        site_url=site_url,
    )
    secrets = infisical_client.get_all_secrets(
        environment=environment, attach_to_os_environ=True
    )
    logger.info(f"Injecting {len(secrets)} environment variables from Infisical:")
    for secret in secrets:
        logger.info(f" - {secret.secret_name}: {mask_string(secret.secret_value)}")


environment = getenv_or_action("ENVIRONMENT", action="warn", default="dev")
if environment not in ["dev", "staging", "prod"]:
    raise ValueError("ENVIRONMENT must be one of 'dev', 'staging' or 'prod'")

inject_environment_variables(environment=environment)

if environment == "dev":
    from app.config.dev import *  # noqa: F401, F403

else:
    from app.config.prod import *  # noqa: F401, F403
