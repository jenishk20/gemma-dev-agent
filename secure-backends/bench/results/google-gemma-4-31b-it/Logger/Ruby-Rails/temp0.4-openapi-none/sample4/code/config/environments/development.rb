require_relative "../application"

Rails.application.configure do
  # Configure development environment
  config.threshold = 100

  # Log to stdout
  config.logger = ActiveSupport::Logger.new(STDOUT)
  config.log_level = :debug

  # Set the server to bind to 0.0.0.0 and port 5000
  config.server.bind = "0.0.0.0"
  config.server.port = 5000

  # Disable caching for development
  config.cache_store = :memory_cache
end