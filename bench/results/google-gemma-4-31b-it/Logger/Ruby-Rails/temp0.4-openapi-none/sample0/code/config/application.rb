require_relative "boot"

require "rails/all"

# Requires these gems in the application's load path.
Bundler.require(*Rails.groups)

module LoggingAPI
  class Application < Rails::Application
    # Initialize configuration defaults
    config.load_defaults 8.0

    # Configure application to run as an API
    config.api_only = true
  end
end