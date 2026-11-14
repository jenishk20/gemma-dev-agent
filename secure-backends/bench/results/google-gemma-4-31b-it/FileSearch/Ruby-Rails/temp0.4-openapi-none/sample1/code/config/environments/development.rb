require "active_support/all"

Rails.application.configure do
  config.load_defaults 8.0

  # Use the standard logger
  config.logger = ActiveSupport::Logger.new(STDOUT)

  # Set default Rails environment to development
  config.env_logger = ActiveSupport::EnvLogger.new(ActiveSupport::Logger.new(STDOUT))

  # Disable caching for development
  config.cache_store = :memory_store
  config.action_controller.perform_caching = false

  # Ensure we don't use assets pipeline as requested
end