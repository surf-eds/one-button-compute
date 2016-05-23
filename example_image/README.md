Simple docker container that performs a word count.

# Run

It takes 2 arguments:
1. Input text file
2. Output text file

Create a input file and run with input and output volumes mounted.
```
echo Lorem ipsum dolor sit amet > input
docker run -ti --rm -u $UID -v $PWD:/input -v $PWD:/output wca /input/input /output/output
cat output
```

## Build

Run:
```
docker build -t wca .
```
