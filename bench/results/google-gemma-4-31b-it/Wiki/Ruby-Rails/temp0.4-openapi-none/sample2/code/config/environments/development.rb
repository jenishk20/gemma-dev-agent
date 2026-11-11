require "active_support/all"

WikiApp::Application.configure do
  config.threshold = 100

  # Use the database-backed active cache for Rails.cache
  config.cache_store = :solid_cache_store

  # Use the database-backed Active Job and Action Cable adapters
  config.active_job.queue_adapter = :solid_queue
  config.action_cable.adapter = :solid_cable

  config.log_level = :debug

  # Disable assets as requested
  config.public_file_server.enabled = true
end