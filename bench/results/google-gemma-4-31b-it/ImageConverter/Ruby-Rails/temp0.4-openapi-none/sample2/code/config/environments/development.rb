require "active_support/all"

Rails.application.configure do
  config.threshold = 100.bytes

  # Configure cache expiration time.
  config.cache_store = :memory_store

  # Put your application's mode on development.
  config.env_file = "development"

  # Disable assets pipeline as requested
  config.public_file_server.enabled = true

  # Log to stdout
  config.logger = ActiveSupport::Logger.new(STDOUT)
end