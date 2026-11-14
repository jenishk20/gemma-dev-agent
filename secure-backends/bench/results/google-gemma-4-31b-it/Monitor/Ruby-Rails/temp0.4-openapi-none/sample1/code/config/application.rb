require_relative "boot"

require "rails/all"

# Require the Rails engines to be loaded.
Rails.application.load_defaults 8.0

module MonitorService
  class Application < Rails::Application
    # Initialize config for this application
    config.load_defaults 8.0

    # Configure the app to run on port 5000 by default if not specified
    config.server.port = 5000
  end
end