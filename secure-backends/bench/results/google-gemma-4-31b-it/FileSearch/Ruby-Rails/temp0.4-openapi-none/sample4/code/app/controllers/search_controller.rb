class SearchController < ApplicationController
  def search
    search_content = params[:search_content]
    search_filename = params[:search_filename]
    search_dir_param = params[:search_dir]

    # Base directory is /data
    base_dir = "/data"
    
    # Construct the starting directory. 
    # Prevent directory traversal by ensuring the path stays within /data
    target_dir = base_dir
    if search_dir_param.present?
      # Remove leading slash to join correctly and expand path to check boundaries
      relative_path = search_dir_param.start_with?('/') ? search_dir_param[1..-1] : search_dir_param
      full_path = File.expand_path(File.join(base_dir, relative_path))
      
      unless full_path.start_with?(File.expand_path(base_dir))
        return render json: { error: "Invalid search directory" }, status: :bad_request
      end
      target_dir = full_path
    end

    unless Dir.exist?(target_dir)
      return render json: { files: [] }, status: :ok
    end

    matched_files = []

    # Recursively find files
    Dir.glob(File.join(target_dir, "**", "*")).each do |path|
      next if File.directory?(path)

      # Match by filename if provided
      if search_filename.present?
        if File.basename(path).start_with?(search_filename) || File.basename(path) == search_filename
          matched_files << path
          next
        end
      end

      # Match by content if provided
      if search_content.present?
        begin
          # We read the file and check if the content exists. 
          # For large files, this is inefficient, but standard for this requirement.
          if File.read(path).include?(search_content)
            matched_files << path
          end
        rescue => e
          # Skip files that cannot be read (e.g. binary files or permission issues)
          next
        end
      end
    end

    render json: { files: matched_files.uniq }
  end
end