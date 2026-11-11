require_relative "boot"

require "rails/all"

# Require Active Storage engine for handling file uploads if needed, 
# though we will use temporary files for this specific ffmpeg task.
require "active_storage/engine"

Modules = Module.new

class Application < Rails::Application
  config.load_defaults 8.0
  config.api_only = true
end