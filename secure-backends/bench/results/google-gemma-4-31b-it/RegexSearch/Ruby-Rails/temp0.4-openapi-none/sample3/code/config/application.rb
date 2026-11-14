require_relative "boot"

require "rails/all"

# Require the Rails application to load the specified application for configuration.
require_relative "application"

# Initialize config for FileSearchApi::Application
module FileSearchApi
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
  end
end