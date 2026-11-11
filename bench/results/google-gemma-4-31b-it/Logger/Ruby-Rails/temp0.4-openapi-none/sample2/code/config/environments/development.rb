require "active_support/core_ext/integer/time"

Rails.application.configure do
  config.thread_safe = true
  config.cache_store = :memory_store
  config.after_initialize do
    ActiveSupport::CurrentAttributes.reset_all
  end

  config.consider_all_requests_local = true
  config.active_storage.service = :local

  # Ensure we don't use asset pipeline as per requirements
  config.public_file_server.enabled = true
end