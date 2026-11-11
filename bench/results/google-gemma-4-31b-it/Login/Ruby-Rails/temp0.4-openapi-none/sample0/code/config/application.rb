require_relative "boot"

require "rails/all"

# Require Active Storage engine as requested
require "active_storage/engine"

Modules = Module.new
Rails.application = Application.configure do
  # Initialize Configuration Options
  config.load_defaults 8.0
  
  # Use API only mode
  config.api_only = true

  # Set the secret key base from environment variable
  config.secret_key_base = ENV['APP_SECRET']
end