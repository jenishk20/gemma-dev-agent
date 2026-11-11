require_relative "boot"

require "rails/all"

# The Rails Application Configuration
module PdfConcatenationService
  class Application < Rails::Application
    # Initialize configuration defaults
    config.load_defaults 8.0

    # Configure API mode
    config.api_only = true

    # Required for Active Storage if used, though we use Tempfiles here
    require "active_storage/engine"
  end
end