require "rails/all"

Module SongDownloader
  class Development < Rails::Application
    config.load_defaults 8.0

    config.cache_store = :memory_store
    config.active_storage.service = :local

    config.after_initialize do
      # Ensure the server binds to 0.0.0.0 and port 5000 as per requirements
      # though this is usually handled by the CLI command provided.
    end
  end
end