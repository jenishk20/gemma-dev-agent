require_relative "boot"

require "rails/all"

# Require the Rails application.
require_relative "application"

module FileSearchApi
  class Application < Rails::Application
    # Initialize config for this application's environment.
    config.load_defaults 8.0

    # Configure the app to be an API
    config.api_only = true
  end
end