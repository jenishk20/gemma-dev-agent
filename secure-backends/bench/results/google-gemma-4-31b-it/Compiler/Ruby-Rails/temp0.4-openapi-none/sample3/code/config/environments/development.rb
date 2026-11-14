require "active_support/core_ext/slogging"

Rails.application.configure do
  # If you have a database configured, you produce a log file in log/development.log
  config.logger = ActiveSupport::Logger.new(STDOUT)

  # Configure logging
  config.log_level = :debug

  # Put your application files into this directory.
  config. autoload_paths << Rails.root.join("lib")

  # Use the database-backed adapters for Rails.cache, Active Job, and Action Cable
  config.cache_store = :solid_cache_store
  config.active_job.queue_adapter = :solid_queue
  config.action_cable.message_synchronizer = :solid_cable
end