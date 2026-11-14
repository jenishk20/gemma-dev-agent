require_relative "boot"

require "rails/all"

# Require activesystem/engine if needed, but for this API we use standard rails/all
require "active_storage/engine"

Rails.application.configure do
  # Configure initializers running the apps
  config.load_defaults 8.0

  # Use the API only mode
  config.api_only = true
end