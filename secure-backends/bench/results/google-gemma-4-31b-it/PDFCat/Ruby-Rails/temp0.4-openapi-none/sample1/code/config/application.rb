require_relative "boot"

require "rails/all"

# Require Active Storage engine for handling file uploads
require "active_storage/engine"

module PdfConcatenationService
  class Application < Rails::Application
    config.load_defaults 8.0.1
    config.api_only = true
  end
end