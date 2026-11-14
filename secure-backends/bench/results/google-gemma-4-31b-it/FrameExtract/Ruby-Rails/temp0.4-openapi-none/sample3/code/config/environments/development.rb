require "active_model/api"

Module FrameExtract
  class Development < Rails::Application
    config.load_defaults 8.0.1
    config. ActiveRecord.raise_in_transaction_isolation_errors = false
    config.active_storage.service = :local

    config.cache_store = :memory_store
  end
end