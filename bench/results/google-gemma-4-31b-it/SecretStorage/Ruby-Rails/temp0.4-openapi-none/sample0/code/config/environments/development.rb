require "rails/application"

Rails.application.configure do
  # Configure for development environment
  config.threshold = 100.bytes

  # Disable assets as requested
  config.public_file_server.enabled = true
  
  # Ensure we don't use sprockets/assets pipeline
  config.assets.enabled = false if config.respond_to?(:assets)
end