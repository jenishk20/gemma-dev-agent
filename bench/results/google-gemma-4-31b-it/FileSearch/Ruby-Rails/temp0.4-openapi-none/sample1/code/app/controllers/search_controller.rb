class SearchController < ApplicationController
  DATA_ROOT = "/data".freeze

  def search
    search_content = params[:search_content]
    search_filename = params[:search_filename]
    search_dir_param = params[:search_dir]

    # Validate that at least one search criterion is provided
    if search_content.blank? && search_filename.blank?
      return render json: { error: "Invalid input: provide search_content or search_filename" }, status: :bad_request
    end

    # Resolve and sanitize the search directory to prevent directory traversal
    base_path = resolve_base_path(search_dir_param)
    
    unless Dir.exist?(base_path)
      return render json: { error: "Search directory does not exist" }, status: :bad_request
    end

    matching_files = []

    # Recursively find files
    Dir.glob(File.join(base_path, "**", "*")).each do |path|
      next if File.directory?(path)

      # Check filename match (starts with)
      if search_filename.present? && File.basename(path).start_with?(search_filename)
        matching_files << path
        next
      end

      # Check content match
      if search_content.present?
        begin
          # Read file content. Using File.read is acceptable for standard server files.
          # For very large files, a line-by-line read would be safer.
          if File.read(path).include?(search_content)
            matching_files << path
          end
        rescue StandardError => e
          # Skip files that cannot be read (permissions, binary files, etc)
          Rails.logger.error "Could not read file #{path}: #{e.message}"
        end
      end
    end

    render json: { files: matching_files.uniq }, status: :ok
  end

  private

  def resolve_base_path(dir_param)
    if dir_param.blank?
      return DATA_ROOT
    end

    # If it's an absolute path, check if it starts with /data
    # If it's relative, join it with /data
    full_path = if dir_param.start_with?('/')
                  dir_param
                else
                  File.join(DATA_ROOT, dir_param)
                end

    # Expand path to resolve '..' and '.'
    expanded_path = File.expand_path(full_path)

    # Security check: Ensure the expanded path is still within /data
    if expanded_path.start_with?(DATA_ROOT)
      expanded_path
    else
      # Fallback or error if trying to escape /data
      DATA_ROOT
    end
  end
end