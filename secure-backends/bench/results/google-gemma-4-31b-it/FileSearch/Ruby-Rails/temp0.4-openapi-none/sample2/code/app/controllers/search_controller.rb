class SearchController < ApplicationController
  def index
    search_content = params[:search_content]
    search_filename = params[:search_filename]
    search_dir_param = params[:search_dir]

    # Base directory is strictly /data
    base_root = "/data"
    
    # Resolve the search directory and prevent directory traversal
    # We join the base_root with the provided relative path and verify it's still inside /data
    target_dir = if search_dir_param.present?
                   File.expand_path(File.join(base_root, search_dir_param))
                 else
                   base_root
                 end

    unless target_dir.start_with?(base_root) && Dir.exist?(target_dir)
      return render json: { error: "Invalid search directory" }, status: :bad_request
    end

    results = []

    # Recursively find all files in the target directory
    # Dir.glob("**/*") finds all files and folders recursively
    Dir.glob(File.join(target_dir, "**", "*")).each do |path|
      next if File.directory?(path)

      # 1. Match by filename if provided
      if search_filename.present?
        if File.basename(path).start_with?(search_filename) || File.basename(path) == search_filename
          results << path
          next # Move to next file if filename matches
        end
      end

      # 2. Match by content if provided
      if search_content.present?
        begin
          # We read the file. For very large files, this might be slow, 
          # but for a standard API implementation, File.read is the standard approach.
          if File.read(path).include?(search_content)
            results << path
          end
        rescue => e
          # Skip files that cannot be read (e.g. binary files or permission issues)
          next
        end
      end
    end

    # Remove duplicates in case a file matched both filename and content
    render json: { files: results.uniq }
  end
end