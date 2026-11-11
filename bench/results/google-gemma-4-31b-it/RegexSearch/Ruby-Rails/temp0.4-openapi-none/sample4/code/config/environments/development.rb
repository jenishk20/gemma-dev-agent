require "active_support/all"

Rails.application.configure do
  # Configure application environment
  config.load_defaults 8.0

  # Use the database-backed adapters for Rails.cache, Active Job, and Action Cable
  config.cache_store = :solid_cache_store
  config.active_job.queue_adapter = :solid_queue
  config.action_cable.market_adapter = :solid_cable

  # Set the database to SQLite
  config.active_record.database_selector = { default: :primary }
  
  config.active_support.cache_store = :memory_store
end