require_relative "boot"

require "rails/all"

# Require Active Storage engine for file handling
require "active_storage/engine"

module FrameExtract
  class Application < Rails::Application
    config.load_defaults 8.0.1
    config.api_only = true
  end
end