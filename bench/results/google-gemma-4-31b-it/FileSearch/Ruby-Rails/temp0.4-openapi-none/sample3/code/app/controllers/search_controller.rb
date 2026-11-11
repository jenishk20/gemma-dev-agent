class SearchController < ApplicationController
  def search
    search_content = params[:search_content]
    search_filename = params[:search_filename]
    search_dir = params[:search_dir]

    # Base directory is /data
    base_path = "/data"
    
    # Handle relative search_dir safely
    target_dir = if search_dir.present?
                   File.expand_path(search_dir, base_path)
                 else
                   base_path
                 end

    # Security check: ensure the resolved path is still within /data to prevent directory traversal
    unless target_dir.start_with?(base_path)
      return render json: { error: "Invalid search directory" }, status: :bad_request
    end

    unless Dir.exist?(target_dir)
      return render json: { files: [] }, status: :ok
    end

    matched_files = []

    # Recursively find all files in the target directory
    Dir.glob(File.join(target_dir, "**", "*")).each do |path|
      next if File.directory?(path)

      # Match filename if provided
      if search_filename.present?
        # The schema says "match the filename", usually implying it starts with or equals
        next unless File.basename(path).start_with?(search_filename)
      end

      # Match content if provided
      if search_content.present?
        begin
          # Read file and check if content exists
          # Using File.read is acceptable for standard server files
          next unless File.read(path).include?(search_content)
        rescue StandardError
          # Skip files that cannot be read (binary, permission issues, etc)
          next
        end
      end

      matched_files << path
    end

    render json: { files: matched_files }, status: :ok
  rescue StandardError => e
    render json: { error: e.message }, status: :bad_request
  end
end