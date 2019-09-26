## $Id: fastqc_parser.R 3691 2015-12-17 11:53:33Z tfrayner $
##
## Rudimentary FastQC data file parser; splits the tables contained
## within a given FastQC data file into a list of data
## frames. Attributes are applied where appropriate (e.g. "summary"
## per module, and an overall "version" attribute applied to the whole
## list).

parseFastQC <- function(filename) {

  results <- list()

  if ( ! file.exists(filename) )
    stop("File not found: ", filename)

  f     <- gzfile(filename, open="r")
  lines <- suppressWarnings(readLines(f))
  close(f)

  line  <- lines[1]
  h <- strsplit(line, "\t")[[1]]

  stopifnot(h[1] == '##FastQC')

  ## Initial development was against version 0.10.1
  attr(results, 'version') <- h[2]

  previous <- 1
  while ( previous < length(lines) ) {

    previous <- previous + 1
    line     <- lines[previous]

    ## Loop over all the lines, picking out modules containing data.
    if ( regexpr('^>>\\b(?!END_MODULE)', line, perl=TRUE) > -1 ) {

      ## Get module title from line, and the summary pass/fail stat.
      summ <- strsplit(substr(line, 3, nchar(line)), "\t")[[1]]
      stopifnot( length(summ) == 2 )
      title <- make.names(summ[1])
      rc <- try(modres <- .parseFastQCModule(lines, previous))
      if ( inherits(rc, 'try-error') ) {
        warning("Unable to parse section: ", title)
      } else {
        results[[title]] <- modres$results
        attr(results[[title]], 'summary') <- summ[2]
      }
      previous <- modres$previous
    }
  }

  return( results )
}

.parseFastQCModule <- function(lines, previous) {

  modres <- list()
  header <- vector(mode='character')
  attrs  <- list()

  while ( previous < length(lines) ) {

    previous <- previous + 1
    line     <- lines[previous]

    if ( regexpr('^>>END_MODULE', line) > -1 ) {

      ## End of the module.
      break
    }
    if ( regexpr('^#\\b', line) > -1 ) {

      if ( length(header) != 0 ) {
        ## Previous headers were actually attributes. The main culprit
        ## here is the read duplicates module.
        suppressWarnings(value <- as.numeric(header[2]))
        if ( is.na(value) ) # Coerce to numeric if possible, otherwise keep as character.
          value <- header[2]
        attrs[ make.names(header[1]) ] <- value
      }

      ## Module table header.
      header <- strsplit(substr(line, 2, nchar(line)), "\t")[[1]]
      stopifnot( length(header) > 0 )
    } else {

      ## Module table body row.
      row <- strsplit(line, "\t")[[1]]
      stopifnot( length(row) == length(header) )
      modres <- append(modres, list(row))
    }
  }

  modres <- data.frame(do.call('rbind', modres), stringsAsFactors=FALSE)
  colnames(modres) <- header

  if ( nrow(modres) > 0 ) {
    for ( n in 1:ncol(modres) ) {
      x <- suppressWarnings(as.numeric(modres[,n]))
      if ( ! any( is.na(x) ) ) {
        modres[,n] <- x
      }
    }
  }

  for ( tag in names(attrs) )
    attr(modres, tag) <- attrs[[tag]]

  return( list(results=modres, previous=previous) )
}
