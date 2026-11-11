require_relative "boot"

require "rails/all"

# The Rails Application.
module FileSearchApi
  class Application < Rails::Application
    # Initialize configuration defaults
    config.load_defaults 8.0

    # Configure application to be an API
    config.api_only = true
  end
end