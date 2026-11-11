require "active_support/all"

MonitorService::Application.configure do
  # Set all ActiveRecord models to raise an error when they are not saved properly
  config.active_record.raise_in_transactional_callbacks = true

  # Set default logger
  config.logger = ActiveSupport::Logger.new(STDOUT)
  
  # Ensure the server binds to 0.0.0.0
  config.hosts.clear
end