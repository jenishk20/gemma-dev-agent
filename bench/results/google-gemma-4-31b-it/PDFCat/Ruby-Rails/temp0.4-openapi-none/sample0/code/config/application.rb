require_relative "boot"

require "rails/all"

# Require Active Storage engine for file handling
require "active_storage/engine"

Bundler.require(*Rails.groups)

module PdfConcatenationService
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
  end
end