require_relative "boot"

require "rails/all"

# Require the Rails application.
require_relative "application"

module CompilationNow
  class Application < Rails::Application
    # Initialize configuration defaults
    config.load_defaults 8.0
    
    # Configure the application for API mode
    config.api_only = true
  end
end