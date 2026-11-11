require "rails/all"

Rails.application.configure do
  config.threshold = 0
  config.cache_store = :memory_store
  config.active_storage.service = :local

  config.consider_all_requests_local = true
  config.active_record.dump_schema_after_migration = false
end