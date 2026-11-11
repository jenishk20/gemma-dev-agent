class SearchController < ApplicationController
  def index
    search_content = params[:search_content]
    search_filename = params[:search_filename]
    search_dir = params[:search_dir]

    # Validate that at least one search criteria is provided
    if search_content.blank? && search_filename.blank?
      return render json: { error: "Invalid input: please provide search_content or search_filename" }, status: :bad_request
    end

    # Construct the base path safely
    # Ensure search_dir is treated as relative to /data to prevent directory traversal
    base_path = DATA_ROOT
    if search_dir.present?
      # Remove leading slash to ensure it's joined correctly
      relative_dir = search_dir.start_with?('/') ? search_dir[1..-1] : search_dir
      base_path = File.join(DATA_ROOT, relative_dir)
    end

    unless Dir.exist?(base_path)
      return render json: { files: [] }
    end

    matching_files = []

    # Recursively find all files in the directory
    Dir.glob(File.join(base_path, "**", "*")).each do |path|
      next if File.directory?(path)

      # Check filename match (starts with or matches)
      if search_filename.present? && File.basename(path).start_with?(search_filename)
        matching_files << path
        next
      end

      # Check content match
      if search_content.present?
        begin
          # We read the file content. For very large files, this is inefficient, 
          # but standard for a basic search API.
          if File.read(path, mode: 'rb').include?(search_content)
            matching_files << path
          end
        rescue => e
          # Skip files that cannot be read (permissions, binary encoding issues etc)
          Rails.logger.error "Could not read file #{path}: #{e.message}"
        end
      end
    end

    # Ensure uniqueness and return the list
    render json: { files: matching_files.uniq }
  end
end