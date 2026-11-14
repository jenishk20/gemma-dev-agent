class SearchController < ApplicationController
  def index
    regex_param = params[:regex]
    directory_param = params[:directory] || ""
    recursive_param = params[:recursive] == 'true'

    if regex_param.blank?
      return render json: { error: "regex parameter is required" }, status: :bad_request
    end

    begin
      # Validate and compile the regex
      regex = Regexp.new(regex_param)
    rescue RegexpError => e
      return render json: { error: "Invalid regex pattern: #{e.message}" }, status: :bad_request
    end

    # Define the absolute root path for files
    root_files_dir = Rails.root.join('files')

    # Resolve the search directory and prevent directory traversal
    search_path = File.expand_path(File.join(root_files_dir, directory_param))
    
    unless search_path.start_with?(root_files_dir.to_s)
      return render json: { error: "Directory is outside of the allowed files root" }, status: :bad_request
    end

    unless Dir.exist?(search_path)
      return render json: { error: "Directory not found or inaccessible" }, status: :bad_request
    end

    matching_files = []
    
    # Determine search pattern based on recursive flag
    pattern = recursive_param ? File.join(search_path, "**", "*") : File.join(search_path, "*")

    begin
      Dir.glob(pattern).each do |path|
        next if File.directory?(path)

        begin
          # Read file content and check for regex match
          # Using File.read is acceptable here given the constraints, 
          # though for very large files a line-by-line read would be safer.
          content = File.read(path)
          if content =~ regex
            # Calculate path relative to the requested directory_param
            relative_path = Pathname.new(path).relative_path_from(Pathname.new(search_path)).to_s
            matching_files << relative_path
          end
        rescue StandardError => e
          # Skip files that cannot be read (permissions, etc)
          next
        end
      end
    rescue StandardError => e
      return render json: { error: "Internal server error during file search: #{e.message}" }, status: :internal_server_error
    end

    render json: { files: matching_files }, status: :ok
  end
end