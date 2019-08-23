import logging
import json
import inspect


class ConfigSpec(object):
    """A class used to create a config spec for ConfigParser"""

    def __init__(self):
        """Initializes the logging"""
        self.logger = logging.getLogger(__name__)

        self.options = {}

    def add_option(self, name, type, default=None):
        """Adds an option to the spec

        Keyword arguments:
          name -- The name of the option to add to the spec.
          type -- An object representing the option's type.
          default -- Optionally, what the option should default to.

        Raises:
          ValueError -- If the option is not a string or type isn't a class.

        """
        # Name must be a string
        if not isinstance(name, basestring):
            raise ValueError("Name must be a string")

        if not inspect.isclass(type):
            raise ValueError("Type must be a class")

        # Ensure that the name is in UTF-8 encoding
        name = name.encode('utf-8')

        self.options[name] = (type, default)

    def return_value_or_default(self, name, value):
        """Validates an option and returns it or the default

        If the value passed in passes validation for its option's type, then it
        will be returned. Otherwise, the default will. This is used for
        validation.

        Keyword arguments:
          name  -- The name of the option to validate for.
          value -- The value to validate.

        Returns:
          string -- The value passed in or the option's default value

        Raises:
          KeyError -- When the option name doesn't exist in the spec.

        """
        if name not in self.options:
            raise KeyError("%s is not a valid option" % name)

        # Separate the type and default from the tuple
        type_check, default = self.options[name]

        # Return the default if the value passed in was wrong, otherwise return
        # the value passed in
        if not isinstance(value, type_check):
            if value is not None:
                self.logger.warning(
                    "Value passed in for option %s was invalid -- ignoring" %
                    name
                )
            else:
                self.logger.debug(
                    "No value set for option %s -- using default" % name)

            return default
        else:
            return value


class ConfigParser(object):
    """A class to make parsing of JSON configs easier.

    This class adds support for both the internal Cardinal config as well as
    config files for plugins. It helps to combine hard-coded defaults with
    values provided by a user (either through a JSON-encoded config file or
    command-line input.)
    """

    def __init__(self, spec):
        """Initializes ConfigParser with a ConfigSpec and initializes logging

        Keyword arguments:
          spec -- Should be a built ConfigSpec

        Raises:
          ValueError -- If a valid config spec is not passed in.

        """
        if not isinstance(spec, ConfigSpec):
            raise ValueError("Spec must be a config spec")

        self.logger = logging.getLogger(__name__)
        self.spec = spec
        self.config = {}

    def _utf8_json(self, json_object, called_by_self=False):
        """Converts json.load() or json.loads() return to UTF-8.

        By default, json.load() will return an object with unicode strings.
        Unfortunately, these cause problems with libraries like Twisted, so we
        need to convert them into UTF-8 encoded strings.

        Keyword arguments:
          json_object -- Dict object returned by json.load() / json.loads().
          called_by_self -- Internal parameter only used for sanity checking.

        Returns:
          dict -- A UTF-8 encoded version of json_object.

        Raises:
          ValueError -- When the json_object isn't a dict.

        """
        if not called_by_self and not isinstance(json_object, dict):
            raise ValueError("Object must be a dict")

        if isinstance(json_object, dict):
            return {
                self._utf8_json(key, True):
                    self._utf8_json(value, True)
                    for key, value in json_object.iteritems()
            }
        elif isinstance(json_object, list):
            return [
                self._utf8_json(element, True)
                for element in json_object
            ]
        elif isinstance(json_object, unicode):
            return json_object.encode('utf-8')
        else:
            return json_object

    def load_config(self, file):
        """Attempts to load a JSON config file for Cardinal.

        Takes a file path, attempts to decode its contents from JSON, then
        validate known config options to see if they can safely be loaded in.
        their place. The final merged dictionary object is saved to the
        If they can't, the default value from the config spec is used in the
        instance and returned.

        Keyword arguments:
          file -- Path to a JSON config file.

        Returns:
          dict -- Dictionary object of the entire config.

        """
        # Attempt to load and parse the config file
        try:
            f = open(file, 'r')
            json_config = self._utf8_json(json.load(f))
            f.close()
        # File did not exist or we can't open it for another reason
        except IOError:
            self.logger.warning(
                "Can't open %s (using defaults / command-line values)" % file
            )
        # Thrown by json.load() when the content isn't valid JSON
        except ValueError:
            self.logger.warning(
                "Invalid JSON in %s, (using defaults / command-line values)" %
                file
            )
        else:
            # For every option,
            for option in self.spec.options:
                try:
                    # If the option wasn't defined in the config, default
                    if option not in json_config:
                        json_config[option] = None

                    self.config[option] = self.spec.return_value_or_default(
                        option, json_config[option])
                except KeyError:
                    self.logger.warning("Option %s not in spec -- ignored" %
                                        option)

        # If we didn't load the config earlier, or there was nothing in it...
        if self.config == {} and self.spec.options != {}:
            for option in self.spec.options:
                # Grab the default
                self.config[option] = self.spec.options[option][1]

        return self.config

    def merge_argparse_args_into_config(self, args):
        """Merges the args returned by argparse.ArgumentParser into the config.

        Keyword arguments:
          args -- The args object returned by argsparse.parse_args().

        Returns:
          dict -- Dictionary object of the entire config.

        """
        for option in self.spec.options:
            try:
                # If the value exists in args and is set, then update the
                # config's value
                value = getattr(args, option)
                if value is not None:
                    self.config[option] = value
            except AttributeError:
                self.logger.debug(
                    "Option %s not in CLI arguments -- not updated" % option
                )

        return self.config
