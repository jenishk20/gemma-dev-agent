require_relative "boot"

require "rails/all"

# Require Active Storage engine as requested
require "active_storage/engine"

module PdfConverter
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
  end
end