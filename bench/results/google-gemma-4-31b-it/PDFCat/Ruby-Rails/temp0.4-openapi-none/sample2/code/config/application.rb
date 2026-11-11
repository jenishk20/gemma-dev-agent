require_relative "boot"

require "rails/all"

# Since we are using Active Storage for temporary file handling (or just standard Rails API)
require "active_storage/engine"

Modules = "PdfConcatenationService"

class Application < Rails::Application
  config.load_defaults 8.0
  config.api_only = true
  
  # Ensure the app can be accessed from 0.0.0.0
  config.servers.defaults = { host: '0.0.0.0', port: 5000 }
end