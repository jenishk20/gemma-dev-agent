require_relative "boot"

require "rails/all"

# Require Active Storage engine as requested
require "active_storage/engine"

module FileSearchApi
  class Application < Rails::Application
    # Initialize config for this application
    config.load_defaults 8.0

    # Configure the app to be an API-only application
    config.api_only = true
  end
end