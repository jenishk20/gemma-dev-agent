require "rails/all"

Rails.application.configure do
  config.load_defaults 8.0

  # Use the database-backed adapters for Rails.cache, Active Job, and Action Cable
  config.active_storage.service = :disk

  # Set timezone
  config.time_zone = "UTC"

  # Log to stdout
  config.logger = ActiveSupport::Logger.new(STDOUT)
end