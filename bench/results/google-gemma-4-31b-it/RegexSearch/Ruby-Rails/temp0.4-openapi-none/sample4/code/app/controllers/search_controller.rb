class SearchController < ApplicationController
  def index
    regex_param = params[:regex]
    directory_param = params[:directory] || ""
    recursive_param = params[:recursive] == 'true'

    if regex_param.blank?
      return render json: { error: "Missing required parameter: regex" }, status: :bad_request
    end

    begin
      regex = Regexp.new(regex_param)
    rescue RegexpError => e
      return render json: { error: "Invalid regex pattern: #{e.message}" }, status: :bad_request
    end

    # Define the root directory for files
    root_path = Rails.root.join('files')
    
    # Resolve the target search directory
    # We ensure the directory is within the root_path to prevent directory traversal attacks
    target_dir = File.expand_path(directory_param, root_path)
    
    unless target_dir.start_with?(root_path.to_s) && Dir.exist?(target_dir)
      return render json: { error: "Invalid or inaccessible directory" }, status: :bad_request
    end

    matching_files = []
    
    # Determine the glob pattern based on recursive flag
    pattern = recursive_param ? File.join(target_dir, "**", "*") : File.join(target_dir, "*")

    begin
      Dir.glob(pattern).each do |path|
        next if File.directory?(path)

        begin
          # Read file content and check for regex match
          content = File.read(path)
          if content =~ regex
            # Calculate path relative to the search directory as per OpenAPI spec
            relative_path = Pathname.new(path).relative_path_from(Pathname.new(target_dir)).to_s
            matching_files << relative_path
          end
        rescue => e
          # Skip files that cannot be read (e.g. permission issues)
          next
        end
      end
    rescue => e
      return render json: { error: "Internal server error during file search: #{e.message}" }, status: :internal_server_error
    end

    render json: { files: matching_files }, status: :ok
  end
end