require_relative "boot"

require "rails/all"

# Require the rails components
require "active_storage/engine"

module CompilationNow
  class Application < Rails::Application
    # Initialize configuration defaults
    config.load_defaults 8.0
    
    # Configure the application for API mode
    config.api_only = true

    # Set the server to bind to 0.0.0.0 and port 5000 as requested
    config.servers.each do |server|
      server.bind_address = '0.0.0.0'
      server.port = 5000
    end
  end
end