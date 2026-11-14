require_relative "boot"

require "rails/all"

# Require Active Storage engine for file handling if needed, 
# though we will process the stream directly for this specific task.
require "active_storage/engine"

Bundler.require(*Rails.groups)

module ZipToTxt
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
    
    # Ensure the server binds to 0.0.0.0 and port 5000 as requested
    config.server = :puma
  end
end