require_relative "boot"

require "rails/all"

# The Rails Application Configuration
module MonitorService
  class Application < Rails::Application
    # Initialize configuration defaults:
    config.load_defaults 8.0

    # Use API only mode
    config.api_only = true
  end
end