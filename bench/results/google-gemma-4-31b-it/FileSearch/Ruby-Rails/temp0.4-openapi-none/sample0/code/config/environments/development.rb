require "active_support/all"

Rails.application.configure do
  config.threshold = 0.5
  config.cache_store = :memory_store
  config.log_level = :debug

  config.active_storage.service = :local

  config.after_initialize do
    # Ensure the data directory exists for development purposes if possible
    begin
      Dir.mkdir(DATA_ROOT) unless Dir.exist?(DATA_ROOT)
    rescue
      # Ignore permission errors in restricted environments
    end
  end
end